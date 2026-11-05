import streamlit as st
from classifier import get_result
import io
import time
import pandas as pd


FORCE_FAIL = set()

def classify(ticket, ticket_id=None, on_retry=None):
    """统一入口：调试开关 + 真实调用（批量跑和重跑都走这里）"""
    if ticket_id in FORCE_FAIL:
        return None, "【调试】注入失败"
    return get_result(ticket, on_retry=on_retry, return_error=True)

st.title("售后单处理助手 v3")
up = st.file_uploader("上传工单 Excel （需要一列工单文本）", type=["xlsx"])
st.caption(f"当前文件:{up.name if up is not None else '还没上传'}")
text = st.text_area("售后单文本", height=150)

if up is not None:
    df = pd.read_excel(io.BytesIO(up.getvalue()))
    st.caption(f"读到 {len(df)} 行 ｜ 列名：{', '.join(df.columns)}")

    if "工单文本" not in df.columns:
        st.error("这张表里没有工单文本这一列，传错文件了")
        st.stop()

MAX_ROWS = 5   # 演示口径：只跑前 5 条；要跑全量改成 21

if up is None:
    st.info("先上传一个 Excel 再开始")
elif st.button("开始批量分类"):
    n = min(MAX_ROWS, len(df))
    bar = st.progress(0.0, text="准备中…")
    rows = []
    t_start = time.perf_counter()

    for i in range(n):
        cur = i + 1

        def on_retry(k, e, cur=cur):
            bar.progress((cur - 1) / n, text=f"第 {cur}/{n} 条 · 第 {k} 次重试…")

        t = str(df.iloc[i]["工单文本"])
        tid = str(df.iloc[i]["工单号"])
        res, err = classify(t, ticket_id=tid, on_retry=on_retry)   #

        row = {"工单号": tid, "原文": t, "错误": err or ""}
        if res is None:
            row.update({"状态": "失败", "需求分类": "", "诉求方式": "",
                        "优先级": "", "回复话术": ""})
        else:
            row.update({"状态": "成功",
                        "需求分类": res.get("需求分类", ""),
                        "诉求方式": res.get("诉求方式", ""),
                        "优先级": res.get("优先级", ""),
                        "回复话术": res.get("回复话术", "")})
        rows.append(row)

        used = time.perf_counter() - t_start
        eta = used / cur * (n - cur)
        bar.progress(cur / n, text=f"已处理 {cur}/{n} · 预计还需 {eta:.0f} 秒")

    st.session_state.res = pd.DataFrame(rows)
    st.session_state.used = n


if "res" in st.session_state:
    r = st.session_state.res
    st.dataframe(
        r,
        column_config={
            "原文": st.column_config.TextColumn("原文", width="medium"),
            "回复话术": st.column_config.TextColumn("回复话术", width="large"),
        },
    )

    ok = int((r["状态"] == "成功").sum())
    bad = st.session_state.used - ok
    if bad == 0:
        st.success(f"处理完成：{ok} 条全部成功")
    elif ok == 0:
        st.error(f"全部失败（{bad} 条）—— 查 url / key / 网络")
    else:
        st.warning(f"部分失败：{ok} 条成功，{bad} 条失败")


    fail_idx = r.index[r["状态"] == "失败"].tolist()
    if fail_idx:
        if st.button(f"重跑失败的 {len(fail_idx)} 条"):
            m = len(fail_idx)
            bar2 = st.progress(0.0, text="重跑中…")
            for j, idx in enumerate(fail_idx):
                cur2 = j + 1
                res2, err2 = classify(r.loc[idx, "原文"], ticket_id=r.loc[idx, "工单号"])
                if res2 is None:
                    r.loc[idx, "错误"] = err2
                else:
                    r.loc[idx, "状态"] = "成功"
                    r.loc[idx, "错误"] = ""
                    r.loc[idx, "需求分类"] = res2.get("需求分类", "")
                    r.loc[idx, "诉求方式"] = res2.get("诉求方式", "")
                    r.loc[idx, "优先级"] = res2.get("优先级", "")
                    r.loc[idx, "回复话术"] = res2.get("回复话术", "")
                bar2.progress(cur2 / m, text=f"重跑 {cur2}/{m}")
            st.session_state.res = r
            st.rerun()
    else:
        st.caption("没有失败条目")

    buf = io.BytesIO()
    r.to_excel(buf, index=False)
    st.download_button(
        "下载结果 Excel",
        data=buf.getvalue(),
        file_name="分类结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if st.button("开始分类"):
    if not text.strip():
        st.warning("先把售后单文本粘进来")
    else:
        with st.spinner("AI正在分析"):
            result = get_result(text)
        if result is None:
            st.session_state.pop("result", None)
            st.error("调用失败，再点一次试试")
        else:
            st.session_state.result = result

if "result" in st.session_state:
    r2 = st.session_state.result
    st.success("分析完成")
    st.write("**需求分类**：", r2.get("需求分类"))
    st.write("**诉求方式**：", r2.get("诉求方式"))
    st.write("**优先级**：", r2.get("优先级"))
    st.text_area("回复话术（可直接复制）", r2.get("回复话术", ""), height=120)