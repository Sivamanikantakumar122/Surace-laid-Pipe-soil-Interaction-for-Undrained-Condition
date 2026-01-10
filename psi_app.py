import streamlit as st
import pandas as pd
from psi_backend import PSI_Undrained_Backend

# Page Config
st.set_page_config(page_title="PSI Undrained Analysis", layout="wide")

st.title("PSI Analysis (Undrained Case)")
st.markdown("---")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Geometry & Soil Params")

# Helper function for number inputs
def num_input(label, val, key=None):
    return st.sidebar.number_input(label, value=float(val), format="%.4f", key=key)

col_sb1, col_sb2 = st.sidebar.columns(2)
with col_sb1:
    dop = num_input("Outer Dia (Dop) [m]", 0.40)
    tp = num_input("Wall Thk (tp) [m]", 0.015)
    z = num_input("Embedment (Z) [m]", 0.10)
    su = num_input("Shear Str (Su) [kPa]", 5.0)

with col_sb2:
    ocr = num_input("OCR", 1.0)
    st_sens = num_input("Sensitivity (St)", 3.0)
    alpha = num_input("Adhesion (alpha)", 1.0)
    rate = num_input("Disp. Rate", 1.0)

st.sidebar.markdown("---")
st.sidebar.header("2. Weight & Constants")
st.markdown("### Developed by **Sivamanikanta Kumar**")
st.markdown("Geotechnical Engineer")
sub_wt_raw = num_input("Submerged Wt (B9 Raw)", 18.0)
su_b14 = num_input("Su Surface (B14 Value)", 5.0)

# --- COEFFICIENT INPUTS (Advanced) ---
with st.sidebar.expander("3. Surface Coefficients (SSR/Prem)"):
    st.markdown("**Concrete Surface**")
    c_ssr_p5 = st.number_input("Conc SSR (P5)", 0.8)
    c_ssr_p50 = st.number_input("Conc SSR (P50)", 1.0)
    c_ssr_p95 = st.number_input("Conc SSR (P95)", 1.2)
    c_prem_p5 = st.number_input("Conc Prem (P5)", 0.2)
    c_prem_p50 = st.number_input("Conc Prem (P50)", 0.25)
    c_prem_p95 = st.number_input("Conc Prem (P95)", 0.3)
    
    st.markdown("**PET Surface**")
    p_ssr_p5 = st.number_input("PET SSR (P5)", 0.7)
    p_ssr_p50 = st.number_input("PET SSR (P50)", 0.9)
    p_ssr_p95 = st.number_input("PET SSR (P95)", 1.1)
    p_prem_p5 = st.number_input("PET Prem (P5)", 0.15)
    p_prem_p50 = st.number_input("PET Prem (P50)", 0.2)
    p_prem_p95 = st.number_input("PET Prem (P95)", 0.25)

# Group coefficients for backend
coeffs_conc = {
    'SSR': [c_ssr_p5, c_ssr_p50, c_ssr_p95],
    'Prem': [c_prem_p5, c_prem_p50, c_prem_p95]
}
coeffs_pet = {
    'SSR': [p_ssr_p5, p_ssr_p50, p_ssr_p95],
    'Prem': [p_prem_p5, p_prem_p50, p_prem_p95]
}

# --- MAIN EXECUTION ---
if st.button("Run Analysis", type="primary"):
    
    # Validation
    if dop <= 0 or su <= 0 or st_sens <= 0:
        st.error("Input Error: Dop, Su, and St must be greater than zero.")
        st.stop()

    # Initialize Backend
    model = PSI_Undrained_Backend(
        dop, tp, z, su, ocr, st_sens, alpha, rate, sub_wt_raw, su_b14,
        coeffs_conc, coeffs_pet
    )
    
    # Run Calculations
    inter = model.calculate_intermediates()
    df_results = model.generate_tables(inter['V'], inter['zeta'], inter['Fl_remain'])
    
    # --- OUTPUT SECTION ---
    
    # 1. Intermediate Data Display
    st.subheader("Intermediate Calculations")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pipe Weight (Wp)", f"{inter['Wp']:.2f} kg/m")
    col2.metric("Flooded Wt (Wpf)", f"{inter['Wpf']:.2f} kN/m")
    col3.metric("Effective Force (V)", f"{inter['V']:.2f} kN/m")
    col4.metric("Wedging (zeta)", f"{inter['zeta']:.2f}")
    
    col5, col6, col7 = st.columns(3)
    col5.metric("Penetration Area", f"{inter['Abm']:.4f} m²")
    col6.metric("Passive Res (Fl)", f"{inter['Fl_remain']:.2f} kN/m")
    
    # Qv Check Logic
    qv_delta = inter['V'] - inter['Qv']
    qv_color = "inverse" if qv_delta < 0 else "normal" # inverse is red in streamlit usually for delta
    col7.metric("Soil Resistance (Qv)", f"{inter['Qv']:.2f} kN/m", 
                delta=f"{qv_delta:.2f} (V - Qv)", delta_color="inverse")

    if inter['V'] >= inter['Qv']:
        st.warning("⚠️ WARNING: Effective Force (V) >= Soil Resistance (Qv). Pipe may sink.")
    else:
        st.success("✅ Check Passed: V < Qv")

    st.markdown("---")

    # 2. Result Tables
    st.subheader("Resistance & Displacement Tables")
    
    # Filter and display Concrete Table
    st.markdown("#### Concrete Surface")
    df_conc = df_results[df_results["Surface"] == "CONCRETE SURFACE"].drop(columns=["Surface"])
    st.dataframe(df_conc, use_container_width=True, hide_index=True)
    
    # Filter and display PET Table
    st.markdown("#### PET Surface")
    df_pet = df_results[df_results["Surface"] == "PET SURFACE"].drop(columns=["Surface"])
    st.dataframe(df_pet, use_container_width=True, hide_index=True)

else:
    st.info("Adjust inputs on the left sidebar and click 'Run Analysis' to see results.")

