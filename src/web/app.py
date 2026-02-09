"""AIbetuchio - მთავარი Streamlit აპლიკაცია."""
import streamlit as st

st.set_page_config(
    page_title="AIbetuchio - საფეხბურთო AI",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚽ AIbetuchio")
st.subheader("საფეხბურთო AI პროგნოზების სისტემა")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 მთავარი პანელი")
    st.write("დღევანდელი პროგნოზები და მეტრიკები")

with col2:
    st.markdown("### 🎯 პროგნოზები")
    st.write("მატჩების პროგნოზები ალბათობებით")

with col3:
    st.markdown("### 💰 ღირებული ფსონები")
    st.write("Value bet-ების რეკომენდაციები")

st.markdown("---")

col4, col5, col6, col7 = st.columns(4)

with col4:
    st.markdown("### 🏆 ლიგის სტატისტიკა")
    st.write("ცხრილი, ფორმა, პირისპირ")

with col5:
    st.markdown("### 📈 ROI ტრეკერი")
    st.write("ფსონების აღრიცხვა და მოგება/ზარალი")

with col6:
    st.markdown("### 📂 მონაცემები")
    st.write("მონაცემების ჩამოტვირთვა და მართვა")

with col7:
    st.markdown("### 🤖 მოდელი")
    st.write("ML მოდელის ინფორმაცია და გადაწვრთნა")

st.markdown("---")
st.info("👈 გამოიყენეთ გვერდითი მენიუ ნავიგაციისთვის")
