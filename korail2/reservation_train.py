from datetime import datetime

import pytz

from docs.conf import source_suffix
from korail2 import *
from load import *
import subprocess
import time
import os

# 한국 시간대 설정
korea_timezone = pytz.timezone('Asia/Seoul')

# 현재 시간 (한국 시간)
korea_now = datetime.now(korea_timezone)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_env(dotenv_path)

korail_id = os.getenv("KORAIL_ID")
korail_pw = os.getenv("KORAIL_PW")

korail = Korail(korail_id, korail_pw)
if not korail.login(korail_id, korail_pw):
    print("로그인 실패")

print("[결제 완료된 티켓]")
for t in korail.tickets():
    print(f"{t} (열차 번호: {t.train_no})")

# 공통 설정
date = '20250714'
psgrs1 = [AdultPassenger(1)]
possible_departure_time = "080000"
cutoff_arrival_time = "130000"
possible_trains_group = "102" # ktx = 100 / 새마을 = 101 / 무궁화 = 102
retry_time = 5

# 역 설정
departure_station = '구미'
possible_transfer_station = '조치원'
destination_station = '영등포'


retry_count = 0  # 재시도 횟수 카운터
while True:
    print()
    try:
        retry_count += 1  # 재시도 1 증가

        # 1차: 바로 가는 열차 검색
        trains_direct = korail.search_train(departure_station, destination_station, date, possible_departure_time, include_no_seats=True, include_waiting_list=True)
        print(f"[{departure_station}에서 {destination_station}로 가는 {possible_departure_time}시 이후 기차 노선 조회 결과]")

        reserved_train_no = None
        is_dir_reserved = False
        for t in trains_direct:
            if t.train_group in possible_trains_group and t.arr_time < cutoff_arrival_time:
                try:
                    seat = korail.reserve(t, psgrs1, ReserveOption.GENERAL_ONLY)
                    print("[직행 예약 성공]", seat)
                    reserved_train_no = t.train_no
                    is_dir_reserved = True  # 직행 예약 성공 플래그 설정
                    # 직행 성공 시 for 루프 종료
                    break
                except SoldOutError:
                    print("[직행 매진]", t)
                except Exception as e:
                    print(f"[직행 예외 발생] {t} - {e}")

        # 직행 예약이 성공했다면 while 루프 종료
        if is_dir_reserved:
            break

        # ---------- 환승 예약 시도 -------------
        trains_1 = korail.search_train(departure_station, possible_transfer_station, date, possible_departure_time, include_no_seats=True, include_waiting_list=True)
        print(f"[1차 노선 검색 결과: {departure_station} → {possible_transfer_station}]")
        reserved_train_no_1 = None
        reserved_train_obj_1 = None

        for t in trains_1:
            if t.train_group in possible_trains_group and t.arr_time < cutoff_arrival_time:
                print(f"{t} (열차 번호: {t.train_no})")
                try:
                    seat = korail.reserve(t, psgrs1, ReserveOption.GENERAL_ONLY)
                    print("[1차 예약 성공]", seat)
                    reserved_train_no_1 = t.train_no
                    reserved_train_obj_1 = seat  # 1차 예약 객체 저장
                    break
                except SoldOutError:
                    print("[1차 매진]", t)
                    continue
                except Exception as e:
                    print(f"[1차 예외 발생] {t} - {e}")
                    continue
        # 리스트나 컬렉션에서 특정 요소를 찾은 후 추가 작업을 하거나, 못 찾았을 때 다른 작업을 하고 싶을 때
        else:  # for 루프가 break 없이 끝났을 경우 (모든 1차 환승 열차 예약 실패)
            print("모든 1차 환승 열차를 시도했지만 예약에 실패했습니다. 다음 재시도를 위해 while 루프를 다시 시작합니다.")
            continue  # while 루프의 다음 반복으로 넘어감

        # 2차 노선 검색은 1차 예약 성공 시에만 시도
        trains_2 = korail.search_train(possible_transfer_station, destination_station, date, possible_departure_time, include_no_seats=True, include_waiting_list=True)
        reserved_train_no_2 = None
        # 2차 예약 성공 여부를 나타내는 플래그
        is_second_leg_reserved = False

        if trains_2:
            for t2 in trains_2:
                if t2.train_no == reserved_train_no_1:  # 이 조건이 문제일 수 있음
                    print(f"{t2} (열차 번호: {t2.train_no})")
                    try:
                        seat2 = korail.reserve(t2, psgrs1, ReserveOption.GENERAL_ONLY)
                        print("[2차 예약 성공]", seat2)
                        reserved_train_no_2 = t2.train_no
                        is_second_leg_reserved = True  # 2차 예약 성공 플래그 설정
                        break
                    except SoldOutError:
                        print(f"[2차 매진] {t2}")
                    except Exception as e:
                        print(f"[2차 예외 발생] {t2} - {e}")

            # 리스트나 컬렉션에서 특정 요소를 찾은 후 추가 작업을 하거나, 못 찾았을 때 다른 작업을 하고 싶을 때
            else:
                print(f"2차 노선 예약 실패 (모든 시도 매진 또는 예외), 1차 예약 취소 후, {retry_count}회차 재시도.")
                try:
                    korail.cancel(reserved_train_obj_1)
                    print(
                        f"✅ 1차 예약 [{reserved_train_obj_1.train_no} {reserved_train_obj_1.dep_name}~{reserved_train_obj_1.arr_name}] 취소 완료.")
                except Exception as cancel_e:
                    print(f"❌ 1차 예약 취소 실패: {cancel_e}")
                continue  # 2차 예약 실패 -> 재시도

        if not trains_2
            print(f"[2차 노선] 검색 결과 없음. 1차 예약 취소 후, {retry_count}회차 재시도.")
            # 2차 노선 검색 결과가 아예 없으므로, 1차 예약 취소
            try:
                korail.cancel(reserved_train_obj_1)
                print(
                    f"✅ 1차 예약 [{reserved_train_obj_1.train_no} {reserved_train_obj_1.dep_name}~{reserved_train_obj_1.arr_name}] 취소 완료.")
            except Exception as cancel_e:
                print(f"❌ 1차 예약 취소 실패: {cancel_e}")
                import traceback
                traceback.print_exc()
            continue  # 2차 노선 없음 -> 재시도

        # 최종 예약 목록 출력 및 종료 (이 부분은 2차 예약이 is_second_leg_reserved 가 True 일때만 실행)
        if is_second_leg_reserved:
            print("환승 예약 성공")
            break  # 환승 예약 성공 후 종료

    except Exception as e:
        print(f"[!!! 중요: 예상치 못한 전체 예외 발생] {e}")
        import traceback

        traceback.print_exc()

    time.sleep(retry_time)
    print(f"예약 실패 (모든 시도 매진 또는 예외), {retry_count}회차 재시도.")


print("\n[최종 예약 목록]")
reservations = korail.reservations()
if reservations:
    for i in range(2):
        subprocess.run(["afplay", "../ding.mp3"])
    print("현재 시간:", korea_now.strftime('%Y-%m-%d %H:%M:%S'))
    print("🎉 \033[1;32m예약 성공! 최종 예약 목록\033[0m 🎉")
    for r in reservations:
        print(f"\033[1;36m{r}\033[0m")
