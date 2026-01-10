import math
import pandas as pd

class PSI_Undrained_Backend:
    def __init__(self, dop, tp, z, su, ocr, st, alpha, rate, sub_wt_raw, su_b14, 
                 coeffs_conc, coeffs_pet):
        """
        Initializes the model with all physical inputs.
        
        Args:
            dop (float): Outer Diameter (m)
            tp (float): Wall Thickness (m)
            z (float): Embedment Depth (m)
            su (float): Undrained Shear Strength (kPa) - B11
            ocr (float): Over Consolidation Ratio
            st (float): Sensitivity
            alpha (float): Adhesion Factor
            rate (float): Displacement Rate
            Bulk_wt_raw (float): Bulk unit Weight Input 
            su_b14 (float): Second Shear Strength parameter 
            coeffs_conc (dict): Dictionary of SSR and Prem for Concrete
            coeffs_pet (dict): Dictionary of SSR and Prem for PET
        """
        self.dop = dop
        self.tp = tp
        self.z = z
        self.su = su
        self.ocr = ocr
        self.st = st
        self.alpha = alpha
        self.rate = rate
        self.sub_wt = sub_wt_raw - 10.05  #  Logic: input - 10.05
        self.su_b14 = su_b14 # Specific input for Fl_remain formula
        
        self.coeffs_conc = coeffs_conc
        self.coeffs_pet = coeffs_pet

        # Constants
        self.pi = math.pi
        self.g = 9.8
        self.klay = 2
        
    def calculate_intermediates(self):
        """Performs Weight, Geometry, and Resistance calculations."""
        dip = self.dop - 2 * self.tp
        
        # 1. Weight Calculations
        wp = (self.pi * (self.dop**2 - dip**2) * 7850) / 4
        wcon = (self.pi * (dip**2) * 1000) / 4
        wb = (self.pi * (self.dop**2) * 1025) / 4
        wpf = ((wp + wcon - wb) * self.g) / 1000
        wpins = (self.pi * (self.dop**2 - dip**2) * (7850 - 1025)) / 4
        
        # Effective Force V
        v = max((wpins * self.klay * self.g / 1000), wpf)
        
        # 2. Geometric & Penetration Resistance (Qv)
        if self.z < (self.dop / 2):
            b_width = 2 * math.sqrt(self.dop * self.z - self.z**2)
            asin_val = math.asin(b_width / self.dop)
            term1 = asin_val * (self.dop**2 / 4)
            term2 = b_width * (self.dop / 4) * math.cos(asin_val)
            abm = term1 - term2
        else:
            abm = (self.pi * self.dop**2 / 8) + self.dop * (self.z - self.dop / 2)
            
        term_bearing = min(6 * (self.z / self.dop)**0.25, 3.4 * (10 * self.z / self.dop)**0.5)
        term_buoyancy = (1.5 * self.sub_wt * abm / (self.dop * self.su))
        qv = (term_bearing + term_buoyancy) * self.dop * self.su
        
        # 3. Wedging and Passive Resistance
        cos_val = 1 - self.z / (self.dop / 2)
        # Safety clamp for Acos domain
        cos_val = max(-1, min(1, cos_val))
        
        beta = math.acos(cos_val)
        
        if beta == 0:
            zeta = 1.0 # Avoid division by zero
        else:
            zeta = (2 * math.sin(beta)) / (beta + math.sin(beta) * math.cos(beta))
            
        fl_remain = self.z * self.rate * (2 * self.su_b14 + 0.5 * self.sub_wt * self.z)
        
        return {
            "Wp": wp, "Wpf": wpf, "V": v, "Abm": abm, 
            "Qv": qv, "zeta": zeta, "Fl_remain": fl_remain
        }

    def generate_tables(self, v, zeta, fl_remain):
        """Generates the Result Tables for Concrete and PET."""
        
        surfaces = [("CONCRETE SURFACE", self.coeffs_conc), ("PET SURFACE", self.coeffs_pet)]
        estimates = ["P5", "P50", "P95"]
        
        all_results = []
        
        for surf_name, coeffs in surfaces:
            for i, est in enumerate(estimates):
                # Fetch coefficients based on estimate index (0=P5, 1=P50, 2=P95)
                ssr = coeffs['SSR'][i]
                prem = coeffs['Prem'][i]
                
                # Main Force Calculations
                abrk = self.alpha * ssr * (self.ocr ** prem) * zeta * self.rate * v
                ares = (1 / self.st) * abrk
                lbrk = (self.alpha * ssr * (self.ocr ** prem) * self.rate * v) + fl_remain
                
                # Lateral Residual Logic
                base_lres = (0.32 + 0.8 * (self.z / self.dop)**0.8) * v
                if i == 0: # P5
                    lres = base_lres / 1.5
                elif i == 2: # P95
                    lres = base_lres * 1.5
                else: # P50
                    lres = base_lres
                
                # Displacement Calculations (converting m to mm)
                dop_mm = self.dop * 1000
                
                # Xb (Axial Break Disp)
                if i == 0: xb = min(1.25, 0.0025 * dop_mm)
                elif i == 1: xb = min(5, 0.01 * dop_mm)
                else: xb = max(50, 0.01 * dop_mm)
                
                # Xr (Axial Res Disp)
                if i == 0: xr = min(7.5, 0.015 * dop_mm)
                elif i == 1: xr = min(30, 0.06 * dop_mm)
                else: xr = max(250, 0.5 * dop_mm)
                
                # Yb (Lat Break Disp)
                if i == 0: yb = (0.004 + 0.02 * (self.z / self.dop)) * dop_mm
                elif i == 1: yb = (0.02 + 0.25 * (self.z / self.dop)) * dop_mm
                else: yb = (0.1 + 0.7 * (self.z / self.dop)) * dop_mm
                
                # Yr (Lat Res Disp)
                if i == 0: yr = 0.6 * dop_mm
                elif i == 1: yr = 1.5 * dop_mm
                else: yr = 2.8 * dop_mm
                
                all_results.append({
                    "Surface": surf_name,
                    "Estimate": est,
                    "Axial Brk (kN/m)": round(abrk, 2),
                    "Xbrk (mm)": round(xb, 2),
                    "Axial Res (kN/m)": round(ares, 2),
                    "Xres (mm)": round(xr, 2),
                    "Lat Brk (kN/m)": round(lbrk, 2),
                    "Ybrk (mm)": round(yb, 2),
                    "Lat Res (kN/m)": round(lres, 2),
                    "Yres (mm)": round(yr, 2)
                })
                
        return pd.DataFrame(all_results)

