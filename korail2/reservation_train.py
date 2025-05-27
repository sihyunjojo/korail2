from korail2 import *
from load import *
import subprocess
import time
import os

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_env(dotenv_path)

korail_id = os.getenv("KORAIL_ID")
korail_pw = os.getenv("KORAIL_PW")

korail = Korail(korail_id, korail_pw)
if not korail.login(korail_id, korail_pw):
    print("로그인 실패")

print("[결제 완료된 티켓]")
for t in korail.tickets():
    print(t)
print()

dep_direct_dep = '구미'
dep_direct_arr = '평택'

dep2_1 = '구미'
dep2_2 = '조치원'
dep2_3 = '평택'

date1 = '20250530'
time1 = '174500'
psgrs1 = [AdultPassenger(1)]
cutoff_arrival_time = "200000"

retry_time = 30
retry_count = 0  # 재시도 횟수 카운터
while True:
    try:
        retry_count += 1  # 재시도 1 증가

        # 1차: 바로 가는 열차 검색
        trains_direct = korail.search_train(dep_direct_dep, dep_direct_arr, date1, time1)

        print("[직행 노선 조회 결과]")
        reserved_train_no = None
        for t in trains_direct:
            if t.train_type_name in ("무궁화호", "ITX-새마을") and t.arr_time < cutoff_arrival_time:
                print(t)
                try:
                    seat = korail.reserve(t, psgrs1, ReserveOption.GENERAL_ONLY)
                    print("[직행 예약 성공]", seat)
                    reserved_train_no = t.train_no
                    break
                except SoldOutError:
                    print("[직행 매진]", t)
                except Exception as e:
                    print(f"[직행 예외 발생] {t} - {e}")

        if reserved_train_no:
            print("\n[최종 예약 목록]")
            reservations = korail.reservations()
            if reservations:
                subprocess.run(["afplay", "../ding.mp3"])
                print("🎉 \033[1;32m예약 성공! 최종 예약 목록\033[0m 🎉")
                for r in reservations:
                    print(f"\033[1;36m{r}\033[0m")
            break  # 직행 성공 시 종료

        print("직행 예약 실패, 환승 예약 시도")

        trains_1 = korail.search_train(dep2_1, dep2_2, date1, time1)
        print("[1차 노선 조회 결과]")
        reserved_train_no_1 = None
        reserved_train_obj_1 = None

        for t in trains_1:
            if t.train_type_name in ("무궁화호", "ITX-새마을") and t.arr_time < cutoff_arrival_time:
                print(t)
                try:
                    seat = korail.reserve(t, psgrs1, ReserveOption.GENERAL_ONLY)
                    print("[1차 예약 성공]", seat)
                    reserved_train_no_1 = t.train_no
                    reserved_train_obj_1 = seat  # 1차 예약 객체 저장
                    break
                except SoldOutError:
                    print("[1차 매진]", t)
                except Exception as e:
                    print(f"[1차 예외 발생] {t} - {e}")

        if not reserved_train_no_1:
            print("1차 예약 실패, 재시도...")
            time.sleep(retry_time)
            continue  # 1차 예약 실패하면 루프 처음으로

            # 2차 노선 검색은 1차 예약 성공 시에만 시도
        trains_2 = korail.search_train(dep2_2, dep2_3, date1, time1)
        reserved_train_no_2 = None
        # 2차 예약 성공 여부를 나타내는 플래그
        is_second_leg_reserved = False

        print(f"\n[2차 노선 검색: {dep2_2} → {dep2_3}]")
        if not trains_2:
            print("[2차 노선] 검색 결과 없음. 1차 예약 취소 후 재시도.")
            # 2차 노선 검색 결과가 아예 없으므로, 1차 예약 취소
            if reserved_train_obj_1:
                try:
                    korail.cancel(reserved_train_obj_1)
                    print(
                        f"✅ 1차 예약 [{reserved_train_obj_1.train_no} {reserved_train_obj_1.dep_name}~{reserved_train_obj_1.arr_name}] 취소 완료.")
                except Exception as cancel_e:
                    print(f"❌ 1차 예약 취소 실패: {cancel_e}")
            else:
                print("⚠️ 1차 예약 객체가 없어 취소할 예약이 없습니다.")
            time.sleep(retry_time)
            continue  # 2차 노선 없음 -> 재시도

        else:  # 2차 노선 검색 결과가 있다면, 예약 시도
            for t2 in trains_2:
                if t2.train_no == reserved_train_no_1:  # 이 조건이 문제일 수 있음
                    print(t2)  # 2차 구간 열차 정보 출력
                    try:
                        seat2 = korail.reserve(t2, psgrs1, ReserveOption.GENERAL_ONLY)
                        print("[2차 예약 성공]", seat2)
                        reserved_train_no_2 = t2.train_no
                        is_second_leg_reserved = True  # 2차 예약 성공 플래그 설정
                        break  # 2차 예약 성공했으니 루프 탈출
                    except SoldOutError:
                        print(f"[2차 매진] {t2}")
                    except Exception as e:
                        print(f"[2차 예외 발생] {t2} - {e}")

            # 2차 예약 시도를 모두 마쳤는데도 성공하지 못했다면 (is_second_leg_reserved가 False라면)
            if not is_second_leg_reserved:
                print("2차 노선 예약 실패 (모든 시도 매진 또는 예외), 1차 예약 취소 후 재시도.")
                if reserved_train_obj_1:  # 1차 예약 객체가 존재하면
                    try:
                        korail.cancel(reserved_train_obj_1)
                        print(
                            f"✅ 1차 예약 [{reserved_train_obj_1.train_no} {reserved_train_obj_1.dep_name}~{reserved_train_obj_1.arr_name}] 취소 완료.")
                    except Exception as cancel_e:
                        print(f"❌ 1차 예약 취소 실패: {cancel_e}")
                else:
                    print("⚠️ 1차 예약 객체가 없어 취소할 예약이 없습니다.")
                time.sleep(retry_time)
                continue  # 2차 예약 실패 -> 재시도

        # 최종 예약 목록 출력 및 종료 (이 부분은 2차 예약이 is_second_leg_reserved 가 True 일때만 실행)
        print("\n[최종 예약 목록]")
        reservations = korail.reservations()
        if reservations:
            subprocess.run(["afplay", "../ding.mp3"])
            print("🎉 \033[1;32m예약 성공! 최종 예약 목록\033[0m 🎉")
            for r in reservations:
                print(f"\033[1;36m{r}\033[0m")
        break  # 예약 성공 후 종료

    except Exception as e:
        print(f"[!!! 중요: 예상치 못한 전체 예외 발생] {e}")
        import traceback

        traceback.print_exc()

    time.sleep(retry_time)
