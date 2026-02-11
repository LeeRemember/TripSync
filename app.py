import streamlit as st
import datetime
import random
import pandas as pd
from chinese_calendar import is_workday, get_holidays

# ==========================================
# 1. 核心算法逻辑
# ==========================================
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

def get_quarter_range(year, quarter):
    start_month = (quarter - 1) * 3 + 1
    start_date = datetime.date(year, start_month, 1)
    if quarter == 4:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, start_month + 3, 1) - datetime.timedelta(days=1)
    return start_date, end_date

def get_schedulable_dates(year, quarter):
    start_date, end_date = get_quarter_range(year, quarter)
    days = []
    curr = start_date
    while curr <= end_date:
        if is_workday(curr):
            days.append(curr)
        curr += datetime.timedelta(days=1)
    if len(days) > 2:
        return days[1:-1]
    return days

# === 核心修改：新增年份数据校验函数 ===
def check_year_support(year):
    """
    检查 chinese_calendar 库中是否包含指定年份的节假日数据。
    原理：尝试获取该年全年的节假日，如果列表为空，说明国务院还没发通知，或者是库没更新。
    """
    try:
        start = datetime.date(year, 1, 1)
        end = datetime.date(year, 12, 31)
        holidays = get_holidays(start, end)
        # 如果一整年一个节假日都没有（连元旦春节都没有），说明数据缺失
        if len(holidays) == 0:
            return False
        return True
    except NotImplementedError:
        return False
    except Exception:
        return False

class TripEvent:
    def __init__(self, start_date, end_date, partners):
        self.start_date = start_date
        self.end_date = end_date
        self.partners = partners
        self.days_count = (end_date - start_date).days + 1
        self.approval_date = get_prev_workday(start_date)
        self.reimburse_date = get_next_workday(end_date)
    def to_dict(self):
        return {
            "开始日期": self.start_date,
            "结束日期": self.end_date,
            "日期显示": f"{self.start_date.strftime('%m-%d')} ~ {self.end_date.strftime('%m-%d')}" if self.days_count > 1 else f"{self.start_date.strftime('%m-%d')}",
            "天数": self.days_count,
            "出差人员": " & ".join(self.partners),
            "审批日期(前)": self.approval_date.strftime('%Y-%m-%d'),
            "报销日期(后)": self.reimburse_date.strftime('%Y-%m-%d')
        }

def run_schedule_logic(people_data, year, quarter):
    workdays = get_schedulable_dates(year, quarter)
    workdays_set = set(workdays)
    daily_occupancy = {d: [] for d in workdays}
    all_events = []

    class SimplePerson:
        def __init__(self, data):
            self.name = data['name']
            self.target_count = data['count']
            self.current_count = 0
            self.blackout_dates = data['blackout']
        def remaining(self): return self.target_count - self.current_count

    people_objs = [SimplePerson(p) for p in people_data]
    total_needed = sum(p.target_count for p in people_objs)
    if total_needed % 2 != 0:
        people_objs.sort(key=lambda x: x.target_count, reverse=True)
        solo_p = people_objs[0]
        for day in workdays:
            if day not in solo_p.blackout_dates and len(daily_occupancy[day]) == 0:
                event = TripEvent(day, day, [solo_p.name])
                all_events.append(event)
                solo_p.current_count += 1
                daily_occupancy[day].append(solo_p.name)
                break

    max_loops = 5000; loop = 0
    while loop < max_loops:
        needy = [p for p in people_objs if p.remaining() > 0]
        if not needy: break
        needy.sort(key=lambda x: x.remaining(), reverse=True)
        if len(needy) < 2: break
        p1, p2 = needy[0], needy[1]
        try_consecutive = (p1.remaining() >= 2 and p2.remaining() >= 2)
        success = False
        trial_days = list(workdays); random.shuffle(trial_days)

        if try_consecutive:
            for day1 in trial_days:
                day2 = day1 + datetime.timedelta(days=1)
                if day2 not in workdays_set: continue
                if len(daily_occupancy[day1]) not in [0, 2] or len(daily_occupancy[day2]) not in [0, 2]: continue
                if any(d in p1.blackout_dates or d in p2.blackout_dates for d in [day1, day2]): continue
                if any(n in daily_occupancy[day1] or n in daily_occupancy[day2] for n in [p1.name, p2.name]): continue
                event = TripEvent(day1, day2, [p1.name, p2.name])
                all_events.append(event)
                p1.current_count += 2; p2.current_count += 2
                daily_occupancy[day1].extend([p1.name, p2.name]); daily_occupancy[day2].extend([p1.name, p2.name])
                success = True; break
        if not success:
            for day in trial_days:
                if len(daily_occupancy[day]) not in [0, 2]: continue
                if day in p1.blackout_dates or day in p2.blackout_dates: continue
                if p1.name in daily_occupancy[day] or p2.name in daily_occupancy[day]: continue
                event = TripEvent(day, day, [p1.name, p2.name])
                all_events.append(event)
                p1.current_count += 1; p2.current_count += 1
                daily_occupancy[day].extend([p1.name, p2.name])
                success = True; break
        if not success: loop += 1; random.shuffle(people_objs)

    all_events.sort(key=lambda x: x.start_date)
    return [e.to_dict() for e in all_events], people_objs

# ==========================================
# 2. Streamlit 界面设计
# ==========================================

st.set_page_config(page_title="TripSync 差旅助手", page_icon="✈️", layout="wide")
st.markdown("<style>.stButton>button {width: 100%; font-weight: bold; border-radius: 8px;}</style>", unsafe_allow_html=True)

if 'people_list' not in st.session_state:
    st.session_state.people_list = []
if 'form_reset_key' not in st.session_state:
    st.session_state.form_reset_key = 0 

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 季度设置")
    year = st.number_input("年份", 2024, 2030, 2025)
    quarter = st.selectbox("季度", [1, 2, 3, 4], index=3, format_func=lambda x: f"第 {x} 季度")
    st.divider()
    
    # === 核心修改：年份校验逻辑 ===
    is_year_valid = check_year_support(year)
    
    if is_year_valid:
        st.success("✅ 节假日数据已就绪")
        st.info("🛡️ **合规保护已开启**\n(自动隐藏每季度首尾工作日)")
    else:
        st.error(f"❌ 警告：系统缺失 {year} 年的节假日数据！")
        st.warning(
            "原因：国务院可能尚未发布该年的放假安排，或软件版本过低。\n\n"
            "⚠️ 为了防止排期错误，系统已暂停服务。"
        )

st.title(f"✈️ 差旅排期助手 ({year} Q{quarter})")

if is_year_valid:
    # ====== 只有年份有效时，才加载下面的核心界面 ======
    @st.cache_data
    def get_safe_workday_df(y, q):
        safe_days = get_schedulable_dates(y, q)
        date_list = []
        for curr in safe_days:
            weekday_num = curr.weekday()
            weekday_str = "一二三四五六日"[weekday_num]
            date_list.append({"日期对象": curr, "日期": curr.strftime('%m-%d'), "星期": f"周{weekday_str}"})
        return pd.DataFrame(date_list)

    df_calendar = get_safe_workday_df(year, quarter)

    # --- 1. 人员录入 ---
    with st.container(border=True):
        st.markdown("#### 👤 1. 添加人员")
        col_input, col_table = st.columns([1, 1.5])
        
        with col_input:
            preset_names = ["刘莉", "刘金武", "冯元发", "卿椿", "徐聪"]
            select_options = preset_names + ["➕ 手动输入新名字..."]
            
            selected_option = st.selectbox("选择姓名", select_options)
            
            if selected_option == "➕ 手动输入新名字...":
                final_name = st.text_input("请输入新姓名", placeholder="例如：王小明")
            else:
                final_name = selected_option
                
            new_count = st.number_input("出差次数", 1, 30, 15)
            st.write("") 
            st.write("") 
            # 按钮保持原样，如果新版 Streamlit 报错，可删除 use_container_width 参数
            add_btn = st.button("➕ 确认添加人员", type="primary", use_container_width=True)

        with col_table:
            st.markdown("**👇 勾选无法出差的日期:**")
            selection = st.dataframe(
                df_calendar[["日期", "星期"]], 
                height=300, 
                hide_index=True,
                width="stretch",
                on_select="rerun", 
                selection_mode="multi-row",
                key=f"date_selector_{st.session_state.form_reset_key}" 
            )

        if add_btn:
            if final_name:
                selected_rows = selection.selection.rows
                blackout_dates = []
                if selected_rows:
                    blackout_dates = df_calendar.iloc[selected_rows]["日期对象"].tolist()
                st.session_state.people_list.append({"name": final_name, "count": new_count, "blackout": blackout_dates})
                st.toast(f"✅ 已添加 {final_name}", icon="🎉")
                st.session_state.form_reset_key += 1 
                st.rerun()
            else:
                st.error("姓名不能为空！")

    # --- 2. 列表展示 ---
    if st.session_state.people_list:
        st.divider()
        st.markdown("#### 📋 已添加人员列表")
        disp_rows = []
        for p in st.session_state.people_list:
            b_str = ", ".join([d.strftime('%m-%d') for d in p['blackout']])
            if len(b_str) > 60: b_str = b_str[:60] + "..."
            if not b_str: b_str = "无"
            disp_rows.append({"姓名": p['name'], "次数": p['count'], "黑名单日期": b_str})
        
        st.dataframe(pd.DataFrame(disp_rows), width="stretch")
        
        if st.button("🗑️ 清空所有人员", type="secondary"):
            st.session_state.people_list = []
            st.session_state.form_reset_key += 1
            st.rerun()

    # --- 3. 生成结果 ---
    st.divider()
    if st.button("🚀 生成排期表", type="primary", use_container_width=True):
        if st.session_state.people_list:
            with st.spinner("正在排期..."):
                results, people_objs = run_schedule_logic(st.session_state.people_list, year, quarter)
                if not results:
                    st.error("计算失败，请检查条件。")
                else:
                    st.success("✅ 计算完成！")
                    st.markdown("### 📊 最终统计")
                    stat_data = []
                    for p in people_objs:
                        status = "✅ 完成" if p.current_count == p.target_count else f"⚠️ 缺 {p.target_count - p.current_count} 次"
                        stat_data.append({"姓名": p.name, "目标": p.target_count, "实际": p.current_count, "状态": status})
                    
                    st.dataframe(pd.DataFrame(stat_data), width="stretch")

                    df_res = pd.DataFrame(results)
                    st.dataframe(df_res[["日期显示", "天数", "出差人员", "审批日期(前)", "报销日期(后)"]], width="stretch", height=600)
                    
                    csv = df_res.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 下载表格", data=csv, file_name=f'Trip_{year}_Q{quarter}.csv', mime='text/csv')
        else:
            st.warning("请先在上一步添加人员！")

else:
    # ====== 如果年份无效，显示大大的错误提示 ======
    st.error("⛔ 当前年份数据缺失，系统已锁定。")
    st.markdown(f"""
    ### 为什么会这样？
    您选择了 **{year}年**，但本程序内置的 `chinese_calendar` 库尚未包含该年的法定节假日数据。
    
    ### 如何解决？
    1. **等待更新**：请等待国务院发布 {year} 年放假安排（通常在上一年的 12 月发布）。
    2. **更新软件**：发布后，请联系开发者重新打包最新版本的软件。
    """)
