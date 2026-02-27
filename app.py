import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
import enum

Base = declarative_base()

class PlatformEnum(enum.Enum):
    SHOPEE = "shopee"
    TIKTOK = "tiktok"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AffiliateAccount(Base):
    __tablename__ = 'affiliate_accounts'
    id = Column(Integer, primary_key=True)
    account_name = Column(String(100), nullable=False)
    platform = Column(Enum(PlatformEnum), nullable=False)
    affiliate_id = Column(String(100), unique=True, nullable=False)
    transactions = relationship("TransactionRecord", back_populates="account")

class TransactionRecord(Base):
    __tablename__ = 'transaction_records'
    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False)
    account_id = Column(Integer, ForeignKey('affiliate_accounts.id'))
    product_name = Column(String(255))
    shop_name = Column(String(255))
    sale_amount = Column(Float, default=0.0)
    commission_amount = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    account = relationship("AffiliateAccount", back_populates="transactions")

engine = create_engine('sqlite:///affiliate_farm.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def seed_dummy_data():
    if session.query(AffiliateAccount).count() == 0:
        acc1 = AffiliateAccount(account_name="Shopee_Main_01", platform=PlatformEnum.SHOPEE, affiliate_id="SHP001")
        acc2 = AffiliateAccount(account_name="Shopee_Sub_02", platform=PlatformEnum.SHOPEE, affiliate_id="SHP002")
        session.add_all([acc1, acc2])
        session.commit()

        for i in range(80):
            txn = TransactionRecord(order_id=f"ORD1_{i}", account_id=acc1.id, commission_amount=5.0, status=OrderStatus.APPROVED)
            session.add(txn)
            
        for i in range(100):
            txn = TransactionRecord(order_id=f"ORD2_{i}", account_id=acc2.id, commission_amount=6.0, status=OrderStatus.APPROVED)
            session.add(txn)
        session.commit()

seed_dummy_data()

st.set_page_config(page_title="Affiliate Farm Dashboard", layout="wide")
st.title("📊 Affiliate Farm Dashboard")
st.markdown("มอนิเตอร์เป้าหมาย: **ค่าคอมมิชชั่น 500 บาท** และ **90 ออเดอร์** ต่อบัญชี")
st.divider()

TARGET_COMMISSION = 500.0
TARGET_ORDERS = 90

results = session.query(
    AffiliateAccount.account_name,
    func.sum(TransactionRecord.commission_amount).label('total_commission'),
    func.count(TransactionRecord.id).label('total_orders')
).outerjoin(TransactionRecord).group_by(AffiliateAccount.id).all()

for row in results:
    acc_name = row.account_name
    comm = row.total_commission or 0.0
    orders = row.total_orders or 0
    
    st.subheader(f"🛒 บัญชี: {acc_name}")
    col1, col2 = st.columns(2)
    
    with col1:
        comm_percent = min(comm / TARGET_COMMISSION, 1.0)
        if comm >= TARGET_COMMISSION:
            st.metric(label="ยอดคอมมิชชั่นสะสม (บาท)", value=f"฿{comm:,.2f}", delta="🎉 ทะลุเป้าหมายแล้ว!")
        else:
            st.metric(label="ยอดคอมมิชชั่นสะสม (บาท)", value=f"฿{comm:,.2f}", delta=f"- ฿{TARGET_COMMISSION - comm:,.2f} (ขาดอีก)", delta_color="inverse")
        st.progress(comm_percent)

    with col2:
        order_percent = min(orders / TARGET_ORDERS, 1.0)
        if orders >= TARGET_ORDERS:
            st.metric(label="จำนวนออเดอร์สะสม", value=f"{orders} ออเดอร์", delta="🎉 ทะลุเป้าหมายแล้ว!")
        else:
            st.metric(label="จำนวนออเดอร์สะสม", value=f"{orders} ออเดอร์", delta=f"- {TARGET_ORDERS - orders} ออเดอร์ (ขาดอีก)", delta_color="inverse")
        st.progress(order_percent)
        
    st.divider()
