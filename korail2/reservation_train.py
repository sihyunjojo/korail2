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


dep1 = '조치원'
arr1 = '평택'
date1 = '20250530'
time1 = '174500'
psgrs1 = [AdultPassenger(1)]
cutoff_arrival_time = "200000"

dep2 = '구미'
arr2 = '조치원'
date2 = date1
psgrs2 = [AdultPassenger(1)]

print("[결제 완료된 티켓]")
for t in korail.tickets():
    print(t)

retry_time = 30
retry_count = 0  # 재시도 횟수 카운터
while True:
    try:
        retry_count += 1  # 재시도 1 증가
        # trains = korail.search_train(dep, arr, date, time, include_no_seats=True)
        trains = korail.search_train(dep1, arr1, date1, time1)

        print("\n[1차 노선 조회 결과]")
        for t in trains:
            if t.train_type_name in ("무궁화호", "ITX-새마을") and t.arr_time < cutoff_arrival_time:
                print(t)

        reserved_train_no = None
        # 예약
        for t in trains:
            if t.train_type_name in ("무궁화호", "ITX-새마을") and t.arr_time < cutoff_arrival_time:
                try:
                    seat = korail.reserve(t, psgrs1, ReserveOption.GENERAL_ONLY)
                    print("[1차 예약 성공]", seat)
                    reserved_train_no = t.train_no
                    break  # 첫 열차만 예약
                except SoldOutError:
                    print("[1차 매진]", t)
                except Exception as e:
                    print(f"[1차 예외 발생] {t} - {e}")

        if reserved_train_no:
            print(f"2차 노선 검색: {dep2} → {arr2}, 동일 열차번호: {reserved_train_no}")

            trains2 = korail.search_train(dep2, arr2, date2, include_no_seats=True)
            for t2 in trains2:
                if t2.train_no == reserved_train_no:
                    try:
                        seat2 = korail.reserve(t2, psgrs2, ReserveOption.GENERAL_ONLY)
                        print("[2차 예약 성공]", seat2)
                        break
                    except SoldOutError:
                        print("[2차 매진]", t2)
                    except Exception as e:
                        print(f"[2차 예외 발생] {t2} - {e}")
        else:
            print("예약 가능한 1차 열차가 없어 2차 예약 생략합니다.")

        print("\n[최종 예약 목록]")
        reservations = korail.reservations()

        if reservations:
            # 시각 + 청각 효과
            subprocess.run(["afplay", "../ding.mp3"])
            print("🎉 \033[1;32m예약 성공! 최종 예약 목록\033[0m 🎉")
            for r in reservations:
                print(f"\033[1;36m{r}\033[0m")  # 진한 시안색으로 예약 내용 출력

            break  # 루프 종료

    except Exception as e:
        print("[전체 예외 발생]", e)

    print(f"재시도 {retry_count}회")
    time.sleep(retry_time)

