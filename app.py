import streamlit as st
import pandas as pd
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==========================================
# ⚙️ 1. ตั้งค่าฐานข้อมูล
# ==========================================
try:
    db_url = st.secrets["DB_URL"]
except:
    db_url = 'sqlite:///affiliate_farm_v5.db'

engine = create_engine(db_url, echo=False)
Base = declarative_base()

# ==========================================
# 🗄️ 2. สร้างตารางข้อมูล
# ==========================================
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    accounts = relationship("AffiliateAccount", back_populates="owner", cascade="all, delete-orphan")

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'))
    ads_cost = Column(Float, default=0.0)  # ✨ ช่องเก็บค่าใช้จ่าย/ค่า Ads
    owner = relationship("User", back_populates="accounts")
    transactions = relationship("TransactionRecord", back_populates="account", cascade="all, delete-orphan")

class TransactionRecord(Base):
    __tablename__ = 'transaction_records'
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), nullable=False)
    account_id = Column(Integer, ForeignKey('affiliate_accounts.id'))
    product_name = Column(String(255))
    product_link = Column(String(500))
    shop_name = Column(String(255))
    shop_link = Column(String(500))
    quantity = Column(Integer, default=1)
    commission_amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    account = relationship("AffiliateAccount", back_populates="transactions")

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# ✨ ทริคพิเศษ: แอบเพิ่มช่อง "ค่าใช้จ่าย" ให้ตารางเดิมโดยไม่ต้องลบทิ้ง
try:
    session.execute(text("ALTER TABLE affiliate_accounts ADD COLUMN ads_cost FLOAT DEFAULT 0.0;"))
    session.commit()
except:
    session.rollback() # ถ้ามีช่องนี้อยู่แล้วให้ข้ามไป

# ==========================================
# 🔐 3. ระบบจัดการผู้ใช้งาน
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

def login_user(username, password):
    user = session.query(User).filter_by(username=username, password=password).first()
    if user:
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user.id
        st.session_state['username'] = user.username
        return True
    return False

# ==========================================
# 🖥️ 4. หน้าจอหลักของแอป
# ==========================================
st.set_page_config(page_title="Affiliate Farm Dashboard", page_icon="🌾", layout="wide")

if not st.session_state['logged_in']:
    st.title("🌾 เข้าสู่ระบบ Affiliate Farm")
    tab1, tab2 = st.tabs(["🔑 เข้าสู่ระบบ", "📝 สมัครสมาชิกใหม่"])
    
    with tab1:
        with st.form("login_form"):
            log_user = st.text_input("ชื่อผู้ใช้ (Username)")
            log_pass = st.text_input("รหัสผ่าน (Password)", type="password")
            if st.form_submit_button("เข้าสู่ระบบ"):
                if login_user(log_user, log_pass):
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
                    
    with tab2:
        with st.form("register_form"):
            reg_user = st.text_input("ตั้งชื่อผู้ใช้ใหม่")
            reg_pass = st.text_input("ตั้งรหัสผ่าน", type="password")
            if st.form_submit_button("สมัครสมาชิก"):
                if session.query(User).filter_by(username=reg_user).first():
                    st.error("ชื่อผู้ใช้นี้มีคนใช้แล้วครับ")
                else:
                    new_user = User(username=reg_user, password=reg_pass)
                    session.add(new_user)
                    session.commit()
                    st.success("สมัครสมาชิกสำเร็จ! กลับไปเข้าสู่ระบบได้เลยครับ")

else:
    # --- เมนูด้านข้าง ---
    st.sidebar.title(f"👤 ยินดีต้อนรับ {st.session_state['username']}")
    menu = st.sidebar.radio("📌 เลือกเมนู", ["📊 Dashboard สรุปยอด", "💼 จัดการบัญชี Affiliate", "📝 บันทึกยอดขาย"])
    
    if st.sidebar.button("🚪 ออกจากระบบ"):
        st.session_state['logged_in'] = False
        st.rerun()

    current_user = session.query(User).get(st.session_state['user_id'])

    # ------------------------------------------
    # เมนูที่ 1: Dashboard สรุปยอด (เพิ่มกำไร-ขาดทุน)
    # ------------------------------------------
    if menu == "📊 Dashboard สรุปยอด":
        st.title("📊 สรุปสถิติและกำไร-ขาดทุน")
        
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        
        if accounts:
            total_comm = 0.0
            total_ads = 0.0
            acc_details = []
            all_transactions = []
            
            # คำนวณรายบัญชี
            for acc in accounts:
                acc_comm = sum([t.commission_amount for t in acc.transactions])
                acc_ads = acc.ads_cost or 0.0
                acc_profit = acc_comm - acc_ads
                
                total_comm += acc_comm
                total_ads += acc_ads
                
                acc_details.append({
                    "ชื่อบัญชี": acc.name,
                    "คอมมิชชันที่ได้ (฿)": acc_comm,
                    "ค่าใช้จ่ายฟาร์ม (฿)": acc_ads,
                    "กำไร/ขาดทุน (฿)": acc_profit
                })
                
                # ดึงรายการขายทั้งหมดไว้ทำกราฟ
                for t in acc.transactions:
                    all_transactions.append({
                        "วันที่": t.created_at.strftime("%Y-%m-%d"),
                        "บัญชี": acc.name,
                        "ร้านค้า": t.shop_name,
                        "จำนวน": t.quantity,
                        "คอมมิชชัน (฿)": t.commission_amount
                    })

            net_profit = total_comm - total_ads

            # 🌟 1. โชว์สถิติภาพรวม
            col1, col2, col3 = st.columns(3)
            col1.metric("💰 ยอดคอมมิชชันรวม", f"฿ {total_comm:,.2f}")
            col2.metric("💸 ต้นทุนฟาร์มรวม", f"฿ {total_ads:,.2f}")
            col3.metric("🎯 กำไร/ขาดทุน สุทธิ", f"฿ {net_profit:,.2f}", delta=float(net_profit))

            st.markdown("---")

            # 🌟 2. โชว์ตารางกำไร-ขาดทุน รายบัญชี
            st.subheader("📋 รายละเอียดกำไร-ขาดทุน (รายบัญชี)")
            df_acc = pd.DataFrame(acc_details)
            
            # ฟังก์ชันแต่งสีเขียว-แดง
            def color_profit(val):
                color = '#10b981' if val > 0 else '#ef4444' if val < 0 else 'gray'
                return f'color: {color}; font-weight: bold;'
            
            st.dataframe(df_acc.style.map(color_profit, subset=['กำไร/ขาดทุน (฿)']), use_container_width=True)

            st.markdown("---")

            # 🌟 3. กราฟและปุ่มโหลดไฟล์ (แบบเดิมที่คุ้นเคย)
            if all_transactions:
                df_trans = pd.DataFrame(all_transactions)
                col_chart, col_dl = st.columns([3, 1])
                with col_chart:
                    st.markdown("**📈 ยอดคอมมิชชันแยกตามร้านค้า**")
                    shop_summary = df_trans.groupby('ร้านค้า')['คอมมิชชัน (฿)'].sum().reset_index()
                    st.bar_chart(shop_summary.set_index('ร้านค้า'))
                
                with col_dl:
                    st.markdown("**📥 ดาวน์โหลดข้อมูลยอดขาย**")
                    csv = df_trans.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("โหลดไฟล์ (CSV)", data=csv, file_name='affiliate_summary.csv', mime='text/csv')

        else:
            st.info("ยังไม่มีข้อมูลบัญชีหรือรายการ ให้ไปเพิ่มในเมนูจัดการบัญชีก่อนนะครับ 🚀")

    # ------------------------------------------
    # เมนูที่ 2: จัดการบัญชี Affiliate (เพิ่มช่องกรอกค่าใช้จ่าย)
    # ------------------------------------------
    elif menu == "💼 จัดการบัญชี Affiliate":
        st.title("💼 จัดการบัญชีและต้นทุนฟาร์ม")
        with st.form("add_account_form"):
            acc_name = st.text_input("ชื่อบัญชี (เช่น TikTok-1, FB-สำรอง)")
            ads_cost = st.number_input("💸 ค่าใช้จ่าย/ค่า Ads ประจำบัญชีนี้ (บาท)", min_value=0.0, step=100.0)
            
            if st.form_submit_button("บันทึกบัญชี"):
                if acc_name:
                    new_acc = AffiliateAccount(name=acc_name, ads_cost=ads_cost, owner_id=current_user.id)
                    session.add(new_acc)
                    session.commit()
                    st.success(f"เพิ่มบัญชี {acc_name} พร้อมต้นทุน {ads_cost} บาท เรียบร้อยแล้ว!")
                    st.rerun()
                else:
                    st.error("กรุณากรอกชื่อบัญชีครับ")
        
        st.markdown("---")
        st.subheader("📋 บัญชีของคุณทั้งหมด")
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        if accounts:
            for acc in accounts:
                st.write(f"- 📌 **{acc.name}** (ต้นทุน: ฿{acc.ads_cost:,.2f})")
        else:
            st.write("ยังไม่มีบัญชี")

    # ------------------------------------------
    # เมนูที่ 3: บันทึกยอดขาย (เหมือนเดิม)
    # ------------------------------------------
    elif menu == "📝 บันทึกยอดขาย":
        st.title("📝 บันทึกยอดคอมมิชชันใหม่")
        accounts = session.query(AffiliateAccount).filter_by(owner_id=current_user.id).all()
        
        if not accounts:
            st.warning("⚠️ กรุณาสร้าง 'บัญชี Affiliate' ในเมนูจัดการบัญชีก่อนครับ")
        else:
            acc_dict = {acc.name: acc.id for acc in accounts}
            
            with st.form("add_transaction_form"):
                selected_acc = st.selectbox("เลือกบัญชี", list(acc_dict.keys()))
                order_id = st.text_input("รหัสคำสั่งซื้อ (Order ID)")
                product_name = st.text_input("ชื่อสินค้า")
                shop_name = st.text_input("ชื่อร้านค้า")
                quantity = st.number_input("จำนวน", min_value=1, step=1)
                commission = st.number_input("ยอดคอมมิชชันที่ได้ (บาท)", min_value=0.0, step=1.0)
                
                if st.form_submit_button("บันทึกยอด"):
                    if order_id and product_name:
                        new_trans = TransactionRecord(
                            order_id=order_id,
                            account_id=acc_dict[selected_acc],
                            product_name=product_name,
                            shop_name=shop_name,
                            quantity=quantity,
                            commission_amount=commission
                        )
                        session.add(new_trans)
                        session.commit()
                        st.success("✅ บันทึกยอดสำเร็จ!")
                    else:
                        st.error("กรุณากรอกรหัสคำสั่งซื้อและชื่อสินค้าครับ")
