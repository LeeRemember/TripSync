import datetime
import random
import csv
from chinese_calendar import is_workday

# ===========================
# 1. 基础类与工具
# ===========================

class TripEvent:
    """表示一次出差事件"""
    def __init__(self, start_date, end_date, partners):
        self.start_date = start_date
        self.end_date = end_date
        self.partners = partners # 出差人员名单
        self.days_count = (end_date - start_date).days + 1
        
        # 自动计算关联日期
        self.approval_date = get_prev_workday(start_date)
        self.reimburse_date = get_next_workday(end_date)

    def to_csv_row(self):
        """转为CSV行数据"""
        date_str = f"{self.start_date.strftime('%Y/%m/%d')}"
        if self.days_count > 1:
            date_str += f"-{self.end_date.strftime('%m/%d')}"
            
        names = ",".join(self.partners)
        return [
            date_str, 
            self.days_count, 
            names, 
            self.approval_date.strftime('%Y/%m/%d'), 
            self.reimburse_date.strftime('%Y/%m/%d')
        ]

class Person:
    def __init__(self, name, target_count, blackout_strs, year):
        self.name = name
        self.target_count = target_count
        self.current_count = 0
        self.blackout_dates = self._parse_dates(year, blackout_strs)

    def _parse_dates(self, year, date_strs):
        dates = []
        for s in date_strs:
            try:
                m, d = map(int, s.split('-'))
                dates.append(datetime.date(year, m, d))
            except:
                pass
        return dates

    def remaining_count(self):
        return self.target_count - self.current_count

# --- 日期计算工具 ---

def get_prev_workday(date):
    d = date - datetime.timedelta(days=1)
    while not is_workday(d):
        d -= datetime.timedelta(days=1)
    return d

def get_next_workday(date):
    d = date + datetime.timedelta(days=1)
    while not is_workday(d):
        d += datetime.timedelta(days=1)
    return d

def get_quarter_workdays(year, quarter):
    start_month = (quarter - 1) * 3 + 1
    start_date = datetime.date(year, start_month, 1)
    if quarter == 4:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, start_month + 3, 1) - datetime.timedelta(days=1)
    
    days = []
    curr = start_date
    while curr <= end_date:
        if is_workday(curr):
            days.append(curr)
        curr += datetime.timedelta(days=1)
    return days

# ===========================
# 2. 核心调度逻辑
# ===========================

def solve_schedule_v4(people, year, quarter):
    print(f"🚀 正在计算 {year}年 Q{quarter} 总控排期表...\n")

    workdays = get_quarter_workdays(year, quarter)
    workdays_set = set(workdays)
    daily_occupancy = {d: [] for d in workdays}
    
    # 用于存储所有生成的行程事件 (Master List)
    all_events = []

    # --- 步骤 1: 平衡奇数总额 (单人行程) ---
    total_needed = sum(p.target_count for p in people)
    if total_needed % 2 != 0:
        people.sort(key=lambda x: x.target_count, reverse=True)
        solo_p = people[0]
        # 找空闲日
        for day in workdays:
            if day not in solo_p.blackout_dates and len(daily_occupancy[day]) == 0:
                event = TripEvent(day, day, [solo_p.name])
                all_events.append(event)
                solo_p.current_count += 1
                daily_occupancy[day].append(solo_p.name)
                break

    # --- 步骤 2: 循环双人调度 ---
    max_loops = 2000
    loop = 0
    
    while loop < max_loops:
        needy = [p for p in people if p.remaining_count() > 0]
        if not needy: break

        needy.sort(key=lambda x: x.remaining_count(), reverse=True)
        if len(needy) < 2: break

        p1 = needy[0]
        p2 = needy[1]
        
        # 策略：优先找连续2天
        try_consecutive = (p1.remaining_count() >= 2 and p2.remaining_count() >= 2)
        success = False
        
        # 随机遍历日期
        trial_days = list(workdays)
        random.shuffle(trial_days)

        # A. 尝试连续两天
        if try_consecutive:
            for day1 in trial_days:
                day2 = day1 + datetime.timedelta(days=1)
                
                if day2 not in workdays_set: continue
                if len(daily_occupancy[day1]) not in [0, 2] or len(daily_occupancy[day2]) not in [0, 2]: continue
                
                # 黑名单检查
                if any(d in p1.blackout_dates or d in p2.blackout_dates for d in [day1, day2]): continue
                # 自身排期检查 (这里简化，因为没有存具体日期，只检查占用表即可，更严谨需存list)
                if p1.name in daily_occupancy[day1] or p1.name in daily_occupancy[day2]: continue
                if p2.name in daily_occupancy[day1] or p2.name in daily_occupancy[day2]: continue

                # 锁定
                event = TripEvent(day1, day2, [p1.name, p2.name])
                all_events.append(event)
                
                p1.current_count += 2
                p2.current_count += 2
                daily_occupancy[day1].extend([p1.name, p2.name])
                daily_occupancy[day2].extend([p1.name, p2.name])
                success = True
                break
        
        # B. 尝试单天
        if not success:
            for day in trial_days:
                if len(daily_occupancy[day]) not in [0, 2]: continue
                if day in p1.blackout_dates or day in p2.blackout_dates: continue
                if p1.name in daily_occupancy[day] or p2.name in daily_occupancy[day]: continue
                
                event = TripEvent(day, day, [p1.name, p2.name])
                all_events.append(event)
                
                p1.current_count += 1
                p2.current_count += 1
                daily_occupancy[day].extend([p1.name, p2.name])
                success = True
                break
        
        if not success:
            loop += 1
            random.shuffle(people)

    # ===========================
    # 3. 输出报表 (按日期排序)
    # ===========================
    
    # 核心：按开始日期排序
    all_events.sort(key=lambda x: x.start_date)

    print("="*85)
    print(f"{'出差日期 (填单)':<20} | {'天数':<6} | {'出差人员':<15} | {'审批日期 (前)':<15} | {'报销日期 (后)':<15}")
    print("-" * 85)

    for e in all_events:
        # 格式化输出
        if e.days_count > 1:
            date_str = f"{e.start_date.strftime('%m-%d')} ~ {e.end_date.strftime('%m-%d')}"
        else:
            date_str = f"{e.start_date.strftime('%m-%d')}"
        
        names_str = " & ".join(e.partners)
        app_str = e.approval_date.strftime('%m-%d')
        reim_str = e.reimburse_date.strftime('%m-%d')
        
        print(f"{date_str:<24} | {e.days_count:<8} | {names_str:<19} | {app_str:<19} | {reim_str:<15}")

    print("="*85)
    
    # 导出 CSV
    filename = f"travel_schedule_{year}_Q{quarter}.csv"
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["出差日期", "天数", "出差人员", "审批日期(建议)", "报销日期(建议)"])
        for e in all_events:
            writer.writerow(e.to_csv_row())
            
    print(f"\n✅ 文件已导出: {filename} (可直接用Excel打开)")
    print("📈 最终统计:")
    for p in people:
        print(f"   {p.name}: {p.current_count}/{p.target_count}")

# ===========================
# 4. 配置区域
# ===========================
if __name__ == "__main__":
    TARGET_YEAR = 2025
    TARGET_QUARTER = 4
    
    # 配置人员 (名字, 总次数, 黑名单列表['MM-DD'], 年份)
    user_configs = [
        Person("刘莉", 18, ['10-10', '10-28', '11-06', '11-07', '11-10', '11-12', '11-13', '11-14', '11-18', '11-27', '12-01', '12-02', '12-04', '12-08', '12-15', '12-18', '12-19', '12-22', '12-24', '12-26'], TARGET_YEAR), # 国庆黑名单
        Person("刘金武", 15, ['11-07', '11-10', '11-11', '11-12', '11-13', '11-14'], TARGET_YEAR),
        Person("冯元发", 18, ['10-16', '10-27', '11-05', '11-17', '11-25', '11-26', '11-27', '12-05', '12-09', '12-18', '12-19', '12-31'], TARGET_YEAR), # 没黑名单，留空 []
        Person("青春", 13, ['10-09', '10-22', '11-10', '11-13', '11-19', '11-26', '11-28', '12-03', '12-08', '12-11', '12-12', '12-15', '12-17', '12-18', '12-19', '12-24', '12-26', '12-30'], TARGET_YEAR),
        Person("徐聪", 20, ['10-20', '11-07', '11-13', '11-24', '12-04', '12-08', '12-09', '12-10', '12-11', '12-15', '12-19', '12-22', '12-24', '12-25'], TARGET_YEAR)
    ]
    
    solve_schedule_v4(user_configs, TARGET_YEAR, TARGET_QUARTER)