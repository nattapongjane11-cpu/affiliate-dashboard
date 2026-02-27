import pandas as pd

st.markdown("---")
st.subheader("📊 สรุปสถิติ Affiliate ของคุณ")

# 1. ดึงข้อมูลจากฐานข้อมูลของ User ปัจจุบันมาแปลงเป็นตาราง (DataFrame)
# (สมมติว่าตัวแปร user_records คือข้อมูลที่คุณ query มาจากฐานข้อมูลแล้ว)
# ถ้าคุณตั้งชื่อตัวแปรอื่น ให้เปลี่ยนชื่อ user_records เป็นชื่อของคุณนะครับ
if user_records:
    # สร้างตารางข้อมูล
    data = []
    for r in user_records:
        data.append({
            "วันที่": r.created_at.strftime("%Y-%m-%d") if r.created_at else "N/A",
            "ชื่อสินค้า": r.product_name,
            "ร้านค้า": r.shop_name,
            "จำนวน": r.quantity,
            "คอมมิชชัน (฿)": r.commission_amount
        })
    df = pd.DataFrame(data)

    # 2. แสดงตัวเลขสรุปยอดรวม (Metrics)
    col1, col2, col3 = st.columns(3)
    col1.metric("ยอดคลิก/รายการทั้งหมด", f"{len(df)} รายการ")
    col2.metric("จำนวนสินค้าที่ขายได้", f"{df['จำนวน'].sum()} ชิ้น")
    col3.metric("คอมมิชชันรวมทั้งหมด", f"฿ {df['คอมมิชชัน (฿)'].sum():,.2f}")

    st.markdown("---")

    # 3. สร้างกราฟแท่งสรุปยอดคอมมิชชัน แยกตาม "ร้านค้า"
    st.markdown("**📈 ยอดคอมมิชชันแยกตามร้านค้า**")
    shop_summary = df.groupby('ร้านค้า')['คอมมิชชัน (฿)'].sum().reset_index()
    # ตั้งค่าให้ชื่อร้านค้าเป็น Index เพื่อให้กราฟแสดงแกน X ได้ถูกต้อง
    st.bar_chart(shop_summary.set_index('ร้านค้า'))

    # 4. ปุ่มดาวน์โหลดข้อมูลเป็นไฟล์ CSV (เปิดใน Excel ได้)
    st.markdown("**📥 ดาวน์โหลดข้อมูล**")
    csv = df.to_csv(index=False).encode('utf-8-sig') # ใช้ utf-8-sig เพื่อให้อ่านภาษาไทยใน Excel ได้ไม่เพี้ยน
    st.download_button(
        label="โหลดไฟล์ข้อมูล (CSV)",
        data=csv,
        file_name='affiliate_summary.csv',
        mime='text/csv',
    )
else:
    st.info("ยังไม่มีข้อมูลรายการ ให้เพิ่มข้อมูลก่อนเพื่อดูสถิตินะครับ 🚀")
