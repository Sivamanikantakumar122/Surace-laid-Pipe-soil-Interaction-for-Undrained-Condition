import streamlit as st
import plotly.graph_objects as go
import psi_backend as backend

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="PSI Analysis Tool", layout="wide")
st.title("Pipe-Soil Interaction Analysis (Undrained)")
st.markdown("---")
st.markdown("**Created by Sivamanikanta Kumar** | Geotechnical Engineer")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("1. Pipeline Geometry")
    Dop = st.number_input("Outer Diameter (m)", value=0.3239, format="%.4f")
    tp = st.number_input("Wall Thickness (m)", value=0.0127, format="%.4f")
    Z = st.number_input("Penetration Depth Z (m)", value=0.05)
    
    st.header("2. Soil Properties")
    Su = st.number_input("Shear Strength Su (kPa)", value=5.0)
    OCR = st.number_input("OCR", value=1.0)
    St = st.number_input("Sensitivity St", value=3.0)
    Su_passive = st.number_input("Passive Su (kPa)", value=5.0)
    gamma_bulk = st.number_input("Bulk Unit Weight (kN/m³)", value=16.0)
    
    st.header("3. Interaction Factors")
    alpha = st.number_input("Adhesion Factor α", value=0.5)
    rate = st.number_input("Rate Factor", value=1.0)
    
    # Dynamic Input Generator for Surfaces
    def get_surface_params(surface_name):
        st.subheader(f"{surface_name} Surface Settings")
        c1, c2 = st.columns(2)
        p5_ssr = c1.number_input(f"{surface_name} P5 SSR", value=0.25)
        p5_prem = c2.number_input(f"{surface_name} P5 Prem", value=1.0)
        
        p50_ssr = c1.number_input(f"{surface_name} P50 SSR", value=0.35)
        p50_prem = c2.number_input(f"{surface_name} P50 Prem", value=1.0)
        
        p95_ssr = c1.number_input(f"{surface_name} P95 SSR", value=0.45)
        p95_prem = c2.number_input(f"{surface_name} P95 Prem", value=1.0)
        
        return {
            f"{surface_name}_P5_SSR": p5_ssr, f"{surface_name}_P5_Prem": p5_prem,
            f"{surface_name}_P50_SSR": p50_ssr, f"{surface_name}_P50_Prem": p50_prem,
            f"{surface_name}_P95_SSR": p95_ssr, f"{surface_name}_P95_Prem": p95_prem,
        }
        
    conc_data = get_surface_params("Concrete")
    pet_data = get_surface_params("PET")

# --- EXECUTE CALCULATION ---
inputs = {
    'Dop': Dop, 'tp': tp, 'Z': Z, 'Su': Su, 'OCR': OCR, 'St': St,
    'alpha': alpha, 'rate': rate, 'gamma_bulk': gamma_bulk, 'Su_passive': Su_passive
}
inputs.update(conc_data)
inputs.update(pet_data)

results = backend.run_psi_analysis(inputs)
metrics = results["metrics"]

# --- RESULTS DASHBOARD ---
st.subheader("Calculation Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Effective Force (V)", f"{metrics['V']:.3f} kN/m")
col2.metric("Vertical Capacity (Qv)", f"{metrics['Qv']:.3f} kN/m")
col3.metric("Wedging Factor (ζ)", f"{metrics['zeta']:.3f}")
col4.metric("Lateral Passive Resist.", f"{metrics['Fl_remain']:.3f} kN/m")

# Stability Alert
if metrics['V'] > metrics['Qv']:
    st.error("FAILURE WARNING: Effective Force (V) > Vertical Capacity (Qv)")
else:
    st.success("STABILITY OK: Effective Force (V) < Vertical Capacity (Qv).")

# --- PLOTTING SECTION ---
st.markdown("---")
st.subheader("Resistance Profiles")

def plot_surface_graphs(surface_name):
    # Create two empty figures (Axial and Lateral)
    fig_ax = go.Figure()
    fig_lat = go.Figure()
    
    colors = {"P5": "green", "P50": "blue", "P95": "red"}
    
    # Filter results for the specific surface
    surface_results = [r for r in results["profiles"] if r["Surface"] == surface_name]
    
    for res in surface_results:
        est = res["Estimate"]
        color = colors.get(est, "black")
        
        # Plot Axial
        ax = res["Axial"]
        fig_ax.add_trace(go.Scatter(
            x=[0, ax["BreakDisp"], ax["ResDisp"], ax["ResDisp"]*1.5],
            y=[0, ax["BreakForce"], ax["ResForce"], ax["ResForce"]],
            mode='lines+markers', name=est, line=dict(color=color)
        ))
        
        # Plot Lateral
        lat = res["Lateral"]
        fig_lat.add_trace(go.Scatter(
            x=[0, lat["BreakDisp"], lat["ResDisp"], lat["ResDisp"]*1.5],
            y=[0, lat["BreakForce"], lat["ResForce"], lat["ResForce"]],
            mode='lines+markers', name=est, line=dict(color=color)
        ))
    
    # Update Layouts
    fig_ax.update_layout(title=f"Axial Resistance ({surface_name})", xaxis_title="Displacement (mm)", yaxis_title="Force (kN/m)", height=350)
    fig_lat.update_layout(title=f"Lateral Resistance ({surface_name})", xaxis_title="Displacement (mm)", yaxis_title="Force (kN/m)", height=350)
    
    return fig_ax, fig_lat

# Tabs for switching surfaces
tab1, tab2 = st.tabs(["Concrete Surface", "PET Surface"])

with tab1:
    fig1, fig2 = plot_surface_graphs("Concrete")
    c1, c2 = st.columns(2)
    c1.plotly_chart(fig1, use_container_width=True)
    c2.plotly_chart(fig2, use_container_width=True)

with tab2:
    fig3, fig4 = plot_surface_graphs("PET")
    c3, c4 = st.columns(2)
    c3.plotly_chart(fig3, use_container_width=True)
    c4.plotly_chart(fig4, use_container_width=True)

