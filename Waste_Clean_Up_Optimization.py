import tkinter as tk
from tkinter import messagebox, ttk  # Add ttk import
from tkintermapview import TkinterMapView
from tkinter import filedialog
import matplotlib.pyplot as plt
import networkx as nx
import requests  # <-- Required for OSRM
from docplex.mp.model import Model
import os
import glob
from datetime import datetime
from PIL import Image, ImageTk
from ttkthemes import ThemedTk  # Add this import
import sv_ttk  # Add this import - pip install sv-ttk

# Home directory
home_dir = os.path.expanduser("~")  # e.g., /home/user
RESULTS_FOLDER = os.path.join(home_dir, "Desktop", "grad project", "app")

def route_distance(p1, p2):
    """
    Returns the driving distance (km) between p1->p2 via the OSRM public API.
    p1, p2 = (latitude, longitude)

    This function requires an internet connection to work.
    """
    lat1, lon1 = p1
    lat2, lon2 = p2
    # Request to OSRM
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        r = requests.get(url, timeout=10)  # 10 seconds timeout
        r.raise_for_status()  # Raises an exception for HTTP errors
        data = r.json()
        dist_m = data["routes"][0]["distance"]  # in meters
        dist_km = dist_m / 1000.0
        return dist_km
    except Exception as e:
        # Return -1 (signal) in case of OSRM service error, etc.
        print("OSRM Error:", e)
        return -1

class MapGUI:

    def draw_heatmap(self, usage_data, all_points):
        # Start a new matplotlib figure
        plt.figure(figsize=(10, 10))
        G = nx.DiGraph()  # Directed graph

        # Add all nodes
        for idx, (lat, lon) in enumerate(all_points):
            G.add_node(idx, pos=(lon, lat))  # (longitude, latitude)

        # Associate density data and draw
        for (x, y), flow in usage_data.items():
            color = self.get_color(flow)
            G.add_edge(x, y, weight=flow, color=color)

        # Set node positions
        pos = nx.get_node_attributes(G, 'pos')

        # Get edge colors and weights
        edges = G.edges(data=True)
        edge_colors = [edge[2]['color'] for edge in edges]
        edge_weights = [edge[2]['weight'] for edge in edges]

        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_size=300, node_color='blue', alpha=0.7)
        nx.draw_networkx_labels(G, pos, font_size=10, font_color='black')
        nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=[w / 5 for w in edge_weights], alpha=0.8)

        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], color='yellow', lw=2, label='Flow ≤ 5'),
            plt.Line2D([0], [0], color='orange', lw=2, label='5 < Flow ≤ 10'),
            plt.Line2D([0], [0], color='red', lw=2, label='Flow > 10')
        ]
        plt.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.05, 1))

        # Adjust layout to make room for legend
        plt.subplots_adjust(right=0.85)

        # Title
        plt.title("Heatmap (Node-to-Node Usage)", fontsize=15)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"heatmap_{timestamp}.png"
        plt.savefig(os.path.join(RESULTS_FOLDER, filename), bbox_inches='tight')
        plt.close()

    def get_color(self, flow):
        if flow <= 5:
            return "yellow"
        elif flow <= 10:
            return "orange"
        else:
            return "red"

    def __init__(self, root):
        self.root = root
        self.root.title("Waste Management Optimization System")
        self.root.geometry("1200x700")
        
        # Apply Sun Valley theme
        sv_ttk.set_theme("dark")
        
        # Configure custom styles
        style = ttk.Style()
        
        # Custom button style
        style.configure(
            'Accent.TButton',
            padding=8,  # Reduced padding
            font=('Segoe UI', 10, 'bold')  # Slightly smaller font
        )
        
        # Custom label styles with smaller fonts
        style.configure(
            'Header.TLabel',
            font=('Segoe UI', 12, 'bold'),
            padding=5,
            background='#2d2d2d'
        )
        
        style.configure(
            'Info.TLabel',
            font=('Segoe UI', 10),
            padding=3,
            background='#2d2d2d'
        )
        
        # Create main frames with gradient effect - smaller left frame
        self.frame_left = ttk.Frame(self.root, style='Card.TFrame')
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Create compact control panel
        control_frame = ttk.Frame(self.frame_left)
        control_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Header
        header = ttk.Label(
            control_frame,
            text="Waste Management\nOptimization",
            style='Header.TLabel',
            justify='center'
        )
        header.pack(pady=(5, 10))
        
        # Point type selection with improved styling
        ttk.Label(
            control_frame,
            text="Select Location Type",
            style='Header.TLabel'
        ).pack(pady=(0, 5))
        
        self.current_mode = tk.StringVar(value="customer")
        modes = [
            ("📍 Customer", "customer"),
            ("🏭 TDWMS", "tdwms"),
            ("🏢 Depot", "depot"),
            ("♻️ Final", "final")
        ]
        
        for label, val in modes:
            ttk.Radiobutton(
                control_frame,
                text=label,
                variable=self.current_mode,
                value=val,
                style='TRadiobutton'
            ).pack(anchor=tk.W, pady=2, padx=10)
            
        ttk.Separator(control_frame).pack(fill=tk.X, pady=10, padx=5)
        
        # Counter labels with icons - more compact
        self.lbl_customer_count = ttk.Label(
            control_frame,
            text="👥 Customer = 0",
            style='Info.TLabel'
        )
        self.lbl_customer_count.pack(anchor=tk.W, padx=10, pady=1)
        
        self.lbl_tdwms_count = ttk.Label(
            control_frame,
            text="🏭 TDWMS = 0",
            style='Info.TLabel'
        )
        self.lbl_tdwms_count.pack(anchor=tk.W, padx=10, pady=1)
        
        self.lbl_depot_count = ttk.Label(
            control_frame,
            text="🏢 Depot = 0",
            style='Info.TLabel'
        )
        self.lbl_depot_count.pack(anchor=tk.W, padx=10, pady=1)
        
        self.lbl_final_count = ttk.Label(
            control_frame,
            text="♻️ Final = 0",
            style='Info.TLabel'
        )
        self.lbl_final_count.pack(anchor=tk.W, padx=10, pady=1)
        
        ttk.Separator(control_frame).pack(fill=tk.X, pady=10, padx=5)
        
        # Custom button style with fixed anchor and alignment
        style.configure(
            'Accent.TButton',
            padding=(15, 8),  # Left padding of 15, vertical padding of 8
            font=('Segoe UI', 10, 'bold'),
            anchor='w'  # Align content to west (left)
        )
        
        # Action buttons with icons - aligned icons and text
        buttons = [
            ("▶️", " Start", self.run_model, 'success'),
            ("📊", " Results", self.show_results, 'info'),
            ("🔄", " Reset", self.reset_points, 'danger'),
            ("🌡️", " Heatmap", self.show_heatmap, 'warning'),
            ("📂", " History", self.show_old_heatmaps, 'primary')
        ]
        
        for icon, text, command, style_class in buttons:
            btn = ttk.Button(
                control_frame,
                text=f"{icon}{text}",  # Combine icon and text with a space
                command=command,
                style='Accent.TButton',
                width=12  # Fixed width for all buttons
            )
            btn.pack(fill=tk.X, padx=10, pady=3)
        
        # Right frame for map
        self.frame_right = ttk.Frame(self.root)
        self.frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initialize map
        self.map_view = TkinterMapView(self.frame_right, width=700, height=600, corner_radius=10)
        self.map_view.pack(fill=tk.BOTH, expand=True)
        self.map_view.set_position(39.0, 35.0)
        self.map_view.set_zoom(6)
        
        # Initialize other attributes
        self.map_paths = []
        self.map_markers = []
        self.customers = []
        self.tdwms = []
        self.depot = []
        self.finals = []
        self.usage_data = {}
        
        # Map click event
        self.map_view.add_left_click_map_command(self.on_map_click)

    def on_hover(self, event, button, color):
        """Create hover effect for buttons"""
        button.configure(style='Custom.TButton')
        
    def on_leave(self, event, button):
        """Remove hover effect for buttons"""
        button.configure(style='Custom.TButton')

    def on_map_click(self, coords):
        """
        coords -> returns a tuple in the form of (latitude, longitude).
        Additionally, if the new point is more than 5 km away from any existing points,
        we reset all inputs.
        """
        lat, lon = coords

        # 1) Check the distance to all existing points via OSRM
        all_existing_points = self.customers + self.tdwms + self.depot + self.finals
        for (ex_lat, ex_lon) in all_existing_points:
            distance_km = route_distance((lat, lon), (ex_lat, ex_lon))
            if distance_km < 0:
                # OSRM Error -1 returned
                messagebox.showwarning(
                    "OSRM Connection Error",
                    "Distance could not be obtained from the road network. Inputs are being reset!"
                )
                self.reset_points()
                return
            if distance_km > 5.0:
                messagebox.showwarning(
                    "Distance Error",
                    f"The selected new point ({distance_km:.2f} km) is more than 5 km away from "
                    "one of the existing points. All inputs are being reset!"
                )
                self.reset_points()
                return

        # 2) If the distance check is passed, proceed to normal addition
        mode = self.current_mode.get()

        if mode == "customer":
            self.customers.append((lat, lon))
            marker = self.map_view.set_marker(lat, lon, text=f"Customer {len(self.customers)}")
            self.map_markers.append(marker)
            self.lbl_customer_count.config(text=f"Customer = {len(self.customers)}")
        elif mode == "tdwms":
            self.tdwms.append((lat, lon))
            marker = self.map_view.set_marker(lat, lon, text=f"TDWMS {len(self.tdwms)}")
            self.map_markers.append(marker)
            self.lbl_tdwms_count.config(text=f"TDWMS = {len(self.tdwms)}")
        elif mode == "depot":
            if len(self.depot) >= 1:
                messagebox.showerror("Error", "You can only add 1 depot.")
                return
            self.depot.append((lat, lon))
            marker = self.map_view.set_marker(lat, lon, text="Depot")
            self.map_markers.append(marker)
            self.lbl_depot_count.config(text=f"Depot = {len(self.depot)}")
        elif mode == "final":
            if len(self.finals) >= 3:
                messagebox.showerror("Error", "You can add a maximum of 3 Final Disposal points.")
                return
            self.finals.append((lat, lon))
            marker = self.map_view.set_marker(lat, lon, text=f"Final {len(self.finals)}")
            self.map_markers.append(marker)
            self.lbl_final_count.config(text=f"Final = {len(self.finals)}")

    def reset_points(self):
        # Clear all point lists
        self.customers.clear()
        self.tdwms.clear()
        self.depot.clear()
        self.finals.clear()

        # Reset labels
        self.lbl_customer_count.config(text="Customer = 0")
        self.lbl_tdwms_count.config(text="TDWMS = 0")
        self.lbl_depot_count.config(text="Depot = 0")
        self.lbl_final_count.config(text="Final = 0")

        # Delete all markers on the map
        for marker in self.map_markers:
            marker.delete()
        self.map_markers.clear()

        # Delete all paths on the map
        for path in self.map_paths:
            path.delete()
        self.map_paths.clear()  # Also clear the path list

        # Clear usage data
        self.usage_data.clear()

    def get_route(self, lat1, lon1, lat2, lon2):
        """
        Gets the route between two points using the OSRM API.
        """
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            coordinates = data["routes"][0]["geometry"]["coordinates"]

            # Convert coordinates returned from OSRM from (lon, lat) to (lat, lon) order
            path_coords = [(lat, lon) for lon, lat in coordinates]
            return path_coords
        except Exception as e:
            print(f"OSRM Route Error: {e}")
            return None

    def show_heatmap(self):
        if not self.usage_data:
            messagebox.showerror(
                "Model Not Run",
                "You must click the 'Start Model' button to run the model before viewing the heatmap."
            )
            return

        all_points = [self.depot[0]] + self.customers + self.tdwms + self.finals

        for (x, y), flow in self.usage_data.items():
            if flow > 0:
                lat1, lon1 = all_points[x]
                lat2, lon2 = all_points[y]

                # Get the route from OSRM
                path_coords = self.get_route(lat1, lon1, lat2, lon2)
                if path_coords:
                    # Determine color based on density
                    color = self.get_color(flow)

                    # Draw the path on the map and add it to the list
                    path = self.map_view.set_path(path_coords, width=5, color=color)
                    self.map_paths.append(path)  # Add the drawn path to the list

        messagebox.showinfo("Heatmap", "The heatmap has been successfully visualized on the map!")

    def run_model(self):
        """
        Constructs and solves the model based on the selected points on the map.
        Also includes the selected points (lat-lon) and distance matrix (uij) information
        in the solution_output.
        """
        if not self.customers or not self.depot or not self.tdwms or not self.finals:
            messagebox.showerror(
                "Missing Point",
                "At least 1 Depot, 1 TDWMS, 1 Customer, and 1 Final must be entered!"
            )
            return

        # [Depot] + [Customers] + [TDWMS] + [Finals]
        all_points = [self.depot[0]] + self.customers + self.tdwms + self.finals
        n_total = len(all_points)

        M = len(self.customers)
        J_count = len(self.tdwms)
        F_count = len(self.finals)

        depot_idx = 0
        customer_idx_list = list(range(1, M+1))
        tdwms_idx_list = list(range(M+1, M+1+J_count))
        final_idx_list = list(range(M+1+J_count, M+1+J_count+F_count))

        T_last = 6
        T = range(0, T_last + 1)

        # Function to find distance over the road
        def dist(i, j):
            dkm = route_distance(all_points[i], all_points[j])
            if dkm < 0:
                # Catch the error before solving the model
                messagebox.showwarning("OSRM Error", "An error occurred in distance calculation, resetting.")
                self.reset_points()
                return 9999999  # Makes the model meaningless
            return dkm

        # Distance matrix
        uij = {}
        for i in range(n_total):
            for j in range(n_total):
                uij[(i, j)] = dist(i, j)

        #---------------------- RECORDING INFORMATION ----------------------
        self.model_solution_text = ""
        self.model_solution_text += "\n--- SELECTED POINTS (Lat, Lon) ---\n"
        for idx, (la, lo) in enumerate(all_points):
            self.model_solution_text += f"  [{idx}] => ({la:.5f}, {lo:.5f})\n"

        self.model_solution_text += "\n--- DISTANCE MATRIX (KM) ---\n"
        for i in range(n_total):
            row_dists = [f"{uij[(i, j)]:.2f}" for j in range(n_total)]
            self.model_solution_text += f"Row {i}: " + "  ".join(row_dists) + "\n"
        #---------------------------------------------------------------------

        # Parameters (example)

        # Wi: Total demand of customer node i (in tonnes).
        # Represents the total amount of waste generated at each customer node (destroyed building).
        # Source: Paper (Section 3.2, Equation 6).
        Wi = {}
        for i in customer_idx_list:
            if i == 1:
                Wi[i] = 120  # Example: Customer 1 generates 120 tonnes of waste.
            elif i == 2:
                Wi[i] = 200  # Example: Customer 2 generates 200 tonnes of waste.
            elif i == 3:
                Wi[i] = 180  # Example: Customer 3 generates 180 tonnes of waste.
            else:
                Wi[i] = 100  # Default: Other customers generate 100 tonnes of waste.

        # ti: Time required to demolish customer node i (in days).
        # Represents the number of days needed to demolish each destroyed building.
        # Source: Paper (Section 3.2, Equation 4).
        ti = {}
        for i in customer_idx_list:
            if i == 1:
                ti[i] = 2  # Example: Customer 1 takes 2 days to demolish.
            elif i == 2:
                ti[i] = 1  # Example: Customer 2 takes 1 day to demolish.
            elif i == 3:
                ti[i] = 3  # Example: Customer 3 takes 3 days to demolish.
            else:
                ti[i] = 2  # Default: Other customers take 2 days to demolish.

        # Ej: Fixed cost for building the TDWMS j (in AUD).
        # Represents the establishment cost for each temporary disaster waste management site (TDWMS).
        # Source: Paper (Section 3.2, Equation 1).
        Ej = {}
        # Oj: Operation cost of TDWMS j (in AUD/day).
        # Represents the daily operational cost for each TDWMS.
        # Source: Paper (Section 3.2, Equation 1).
        Oj = {}
        # sj: Capacity of TDWMS j (in tonnes).
        # Represents the maximum amount of waste that can be stored at each TDWMS.
        # Source: Paper (Section 3.2, Equation 24).
        sj = {}
        for j in tdwms_idx_list:
            Ej[j] = 8000   # Example: TDWMS j has an establishment cost of 8000 AUD.
            Oj[j] = 1500   # Example: TDWMS j has an operational cost of 1500 AUD/day.
            sj[j] = 25000  # Example: TDWMS j has a capacity of 25000 tonnes.

        # m: Number of demolition machines available.
        # Represents the total number of machines available for demolishing buildings.
        # Source: Paper (Section 3.2, Equation 5).
        m = 1 # Example: 2 demolition machines are available.

        # K: Set of available collection vehicles in a day.
        # Represents the collection vehicles available for waste collection.
        # Source: Paper (Section 3.2, Equation 14).
        K = [1]  # Example: 2 collection vehicles are available.

        # K0: Set of available transportation vehicles in a day.
        # Represents the transportation vehicles available for waste transportation.
        # Source: Paper (Section 3.2, Equation 23).
        K0 = [1]  # Example: 1 transportation vehicle is available.

        # Q: Capacity of each collection vehicle (in tonnes).
        # Represents the maximum amount of waste that can be transported by a collection vehicle in one trip.
        # Source: Paper (Section 3.2, Equation 9).
        Q = 50  # Example: Each collection vehicle can carry 50 tonnes of waste.

        # Q0: Capacity of each transportation vehicle (in tonnes).
        # Represents the maximum amount of waste that can be transported by a transportation vehicle in one trip.
        # Source: Paper (Section 3.2, Equation 18).
        Q0 = 40  # Example: Each transportation vehicle can carry 40 tonnes of waste.

        # v: Speed of collection vehicles (in km/h).
        # Represents the speed at which collection vehicles travel.
        # Source: Paper (Section 3.2, Equation 10).
        v = 25  # Example: Collection vehicles travel at 25 km/h.

        # v0: Speed of transportation vehicles (in km/h).
        # Represents the speed at which transportation vehicles travel.
        # Source: Paper (Section 3.2, Equation 19).
        v0 = 30  # Example: Transportation vehicles travel at 30 km/h.

        # R: Total working time of a vehicle in a day (in minutes).
        # Represents the maximum daily working time for each vehicle (collection or transportation).
        # Source: Paper (Section 3.2, Equations 10 and 19).
        R = 150  # Example: Each vehicle can work for 150 minutes per day.

        # g: Waste recycling rate.
        # Represents the fraction of waste that can be recycled.
        # Source: Paper (Section 3.2, Equation 16).
        g = 0.35  # Example: 35% of the waste can be recycled.

        # ck: Cost per kilometer for collection vehicles (in AUD/km).
        # Represents the cost of traveling one kilometer for a collection vehicle.
        # Source: Paper (Section 3.2, Equation 1).
        ck = 100  # Example: Collection vehicles cost 100 AUD per kilometer.

        # ck0: Cost per kilometer for transportation vehicles (in AUD/km).
        # Represents the cost of traveling one kilometer for a transportation vehicle.
        # Source: Paper (Section 3.2, Equation 1).
        ck0 = 150  # Example: Transportation vehicles cost 150 AUD per kilometer.



        # -------------------- Stage 1: Minimize Time --------------------
        mdl_time = Model(name="Time Minimization")
        mdl_time.parameters.timelimit = 36000  # 10 hours
        mdl_time.parameters.mip.tolerances.mipgap = 0.15

        # Decision Variables
        xid = mdl_time.binary_var_matrix(customer_idx_list, range(1, T_last+1), name="xid")
        yid = mdl_time.binary_var_matrix(customer_idx_list, range(1, T_last+1), name="yid")
        cid = mdl_time.continuous_var_matrix(customer_idx_list, T, name="cid", lb=0)
        rid = mdl_time.continuous_var_matrix(customer_idx_list, T, name="rid", lb=0)
        sd = mdl_time.binary_var_list(T, name="sd")

        xj = mdl_time.binary_var_dict(tdwms_idx_list, name="xj")
        rjd = mdl_time.continuous_var_matrix(tdwms_idx_list, T, name="rjd", lb=0)
        lj = mdl_time.continuous_var_dict(tdwms_idx_list, name="lj", lb=0)

        aijd = mdl_time.integer_var_cube(range(n_total), range(n_total), range(1, T_last+1), name="aijd", lb=0)
        zijd = mdl_time.continuous_var_cube(customer_idx_list, tdwms_idx_list, range(1, T_last+1),
                                        name="zijd", lb=0)

        bjld = mdl_time.integer_var_cube(range(n_total), range(n_total), range(1, T_last+1), name="bjld", lb=0)
        fjld = mdl_time.continuous_var_cube(tdwms_idx_list, final_idx_list, range(1, T_last+1),
                                        name="fjld", lb=0)

        # Constraints
        mdl_time.add_constraint(mdl_time.sum(xj[j] for j in tdwms_idx_list) >= 1, "min_one_tdwms_open")

        for i in customer_idx_list:
            mdl_time.add_constraint(mdl_time.sum(xid[i, d] for d in range(1, T_last+1)) == 1)

        for i in customer_idx_list:
            for d in range(1, T_last+1):
                mdl_time.add_constraint(
                    yid[i, d] == mdl_time.sum(xid[i, dd] for dd in range(max(1, d - ti[i] + 1), d+1))
                )

        for d in range(1, T_last+1):
            mdl_time.add_constraint(mdl_time.sum(yid[i, d] for i in customer_idx_list) <= m)

        for i in customer_idx_list:
            for d in range(0, T_last+1):
                if d == 0:
                    mdl_time.add_constraint(cid[i, 0] == Wi[i])
                else:
                    mdl_time.add_constraint(
                        cid[i, d] == Wi[i] - mdl_time.sum(zijd[i, j, dd]
                                                        for j in tdwms_idx_list for dd in range(1, d+1))
                    )

        for i in customer_idx_list:
            for d in range(1, T_last+1):
                if d == 1:
                    mdl_time.add_constraint(rid[i, 0] == 0)
                    mdl_time.add_constraint(
                        yid[i, 1] * (Wi[i]/ti[i]) ==
                        rid[i, 1] + mdl_time.sum(zijd[i, j, 1] for j in tdwms_idx_list)
                    )
                else:
                    mdl_time.add_constraint(
                        yid[i, d] * (Wi[i]/ti[i]) + rid[i, d-1]
                        == rid[i, d] + mdl_time.sum(zijd[i, j, d] for j in tdwms_idx_list)
                    )

        for i in customer_idx_list:
            mdl_time.add_constraint(rid[i, T_last] == 0)

        for i in customer_idx_list:
            for j in tdwms_idx_list:
                for d in range(1, T_last+1):
                    mdl_time.add_constraint(zijd[i, j, d] <= aijd[i, j, d] * Q)

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(aijd[x, y, d] * (uij[(x, y)]/v) * 60
                            for x in range(n_total) for y in range(n_total))
                <= len(K)*R
            )

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(aijd[depot_idx, i, d] for i in customer_idx_list)
                == mdl_time.sum(aijd[j, depot_idx, d] for j in tdwms_idx_list)
            )

        for i in customer_idx_list:
            for d in range(1, T_last+1):
                mdl_time.add_constraint(
                    mdl_time.sum(aijd[x, i, d] for x in [depot_idx]+tdwms_idx_list)
                    == mdl_time.sum(aijd[i, y, d] for y in [depot_idx]+tdwms_idx_list)
                )

        for j in tdwms_idx_list:
            for d in range(1, T_last+1):
                mdl_time.add_constraint(
                    mdl_time.sum(aijd[x, j, d] for x in [depot_idx]+customer_idx_list)
                    == mdl_time.sum(aijd[j, y, d] for y in [depot_idx]+customer_idx_list)
                )

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(aijd[depot_idx, i, d] for i in customer_idx_list) <= len(K)
            )

        for i in customer_idx_list:
            mdl_time.add_constraint(
                mdl_time.sum(zijd[i, j, d] for j in tdwms_idx_list for d in range(1, T_last+1)) == Wi[i]
            )

        for j in tdwms_idx_list:
            for d in range(0, T_last+1):
                if d == 0:
                    mdl_time.add_constraint(rjd[j, 0] == 0)
                else:
                    mdl_time.add_constraint(
                        (1-g)*mdl_time.sum(zijd[i, j, d] for i in customer_idx_list)
                        + rjd[j, d-1]
                        == rjd[j, d] + mdl_time.sum(fjld[j, f, d] for f in final_idx_list)
                    )

        for j in tdwms_idx_list:
            mdl_time.add_constraint(rjd[j, T_last] == 0)

        for j in tdwms_idx_list:
            for f in final_idx_list:
                for d in range(1, T_last+1):
                    mdl_time.add_constraint(fjld[j, f, d] <= bjld[j, f, d]*Q0)

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(bjld[x, y, d] * (uij[(x, y)]/v0)*60
                            for x in range(n_total) for y in range(n_total))
                <= len(K0)*R
            )

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(aijd[depot_idx, i, d] for i in customer_idx_list + tdwms_idx_list) >= 1
            )

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(bjld[depot_idx, j, d] for j in tdwms_idx_list)
                == mdl_time.sum(bjld[f, depot_idx, d] for f in final_idx_list)
            )

        for j in tdwms_idx_list:
            for d in range(1, T_last+1):
                mdl_time.add_constraint(
                    mdl_time.sum(bjld[x, j, d] for x in final_idx_list+[depot_idx])
                    == mdl_time.sum(bjld[j, y, d] for y in final_idx_list+[depot_idx])
                )

        for f in final_idx_list:
            for d in range(1, T_last+1):
                mdl_time.add_constraint(
                    mdl_time.sum(bjld[x, f, d] for x in tdwms_idx_list+[depot_idx])
                    == mdl_time.sum(bjld[f, x, d] for x in tdwms_idx_list+[depot_idx])
                )

        for d in range(1, T_last+1):
            mdl_time.add_constraint(
                mdl_time.sum(bjld[depot_idx, j, d] for j in tdwms_idx_list) <= len(K0)
            )

        for j in tdwms_idx_list:
            for d in range(0, T_last+1):
                mdl_time.add_constraint(rjd[j, d] <= xj[j]*sj[j])

        mdl_time.add_constraint(
            (1-g)*mdl_time.sum(zijd[i, j, d]
                            for i in customer_idx_list for j in tdwms_idx_list for d in range(1, T_last+1))
            == mdl_time.sum(fjld[j, f, d]
                        for j in tdwms_idx_list for f in final_idx_list for d in range(1, T_last+1))
        )

        for d in range(1, T_last+1):
            for i in customer_idx_list:
                mdl_time.add_constraint(sd[d] >= 1 - cid[i, d]/Wi[i])
            for j in tdwms_idx_list:
                mdl_time.add_constraint(sd[d] >= 1 - rjd[j, d]/sj[j])

        for j in tdwms_idx_list:
            mdl_time.add_constraint(
                lj[j] <= ((T_last+1)-mdl_time.sum(sd[d] for d in range(T_last+1))+1)*Oj[j]
                        + (T_last+1)*Oj[j]*(1 - xj[j])
            )

        # Objective: Minimize total clean-up time
        totalTime = mdl_time.sum(sd[d] for d in range(1, T_last + 1))
        mdl_time.minimize(totalTime)

        # Solve the model
        print(">>> Solving Stage 1: Minimizing Time...")
        solution_time = mdl_time.solve(log_output=True)
        if solution_time:
            optimal_time = solution_time.objective_value
            print("Optimal Time:", optimal_time)
        else:
            print("No solution found for time minimization.")
            return

        # -------------------- Stage 2: Minimize Cost with Time Constraint --------------------
        mdl_cost = Model(name="Cost Minimization")
        mdl_cost.parameters.timelimit = 36000  # 10 hours

        # Decision Variables
        xid = mdl_cost.binary_var_matrix(customer_idx_list, range(1, T_last+1), name="xid")
        yid = mdl_cost.binary_var_matrix(customer_idx_list, range(1, T_last+1), name="yid")
        cid = mdl_cost.continuous_var_matrix(customer_idx_list, T, name="cid", lb=0)
        rid = mdl_cost.continuous_var_matrix(customer_idx_list, T, name="rid", lb=0)
        sd = mdl_cost.binary_var_list(T, name="sd")

        xj = mdl_cost.binary_var_dict(tdwms_idx_list, name="xj")
        rjd = mdl_cost.continuous_var_matrix(tdwms_idx_list, T, name="rjd", lb=0)
        lj = mdl_cost.continuous_var_dict(tdwms_idx_list, name="lj", lb=0)

        aijd = mdl_cost.integer_var_cube(range(n_total), range(n_total), range(1, T_last+1), name="aijd", lb=0)
        zijd = mdl_cost.continuous_var_cube(customer_idx_list, tdwms_idx_list, range(1, T_last+1),
                                        name="zijd", lb=0)

        bjld = mdl_cost.integer_var_cube(range(n_total), range(n_total), range(1, T_last+1), name="bjld", lb=0)
        fjld = mdl_cost.continuous_var_cube(tdwms_idx_list, final_idx_list, range(1, T_last+1),
                                        name="fjld", lb=0)

        # Constraints (same as Stage 1)
        mdl_cost.add_constraint(mdl_cost.sum(xj[j] for j in tdwms_idx_list) >= 1, "min_one_tdwms_open")

        for i in customer_idx_list:
            mdl_cost.add_constraint(mdl_cost.sum(xid[i, d] for d in range(1, T_last+1)) == 1)

        for i in customer_idx_list:
            for d in range(1, T_last+1):
                mdl_cost.add_constraint(
                    yid[i, d] == mdl_cost.sum(xid[i, dd] for dd in range(max(1, d - ti[i] + 1), d+1))
                )

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(mdl_cost.sum(yid[i, d] for i in customer_idx_list) <= m)

        for i in customer_idx_list:
            for d in range(0, T_last+1):
                if d == 0:
                    mdl_cost.add_constraint(cid[i, 0] == Wi[i])
                else:
                    mdl_cost.add_constraint(
                        cid[i, d] == Wi[i] - mdl_cost.sum(zijd[i, j, dd]
                                                        for j in tdwms_idx_list for dd in range(1, d+1))
                    )

        for i in customer_idx_list:
            for d in range(1, T_last+1):
                if d == 1:
                    mdl_cost.add_constraint(rid[i, 0] == 0)
                    mdl_cost.add_constraint(
                        yid[i, 1] * (Wi[i]/ti[i]) ==
                        rid[i, 1] + mdl_cost.sum(zijd[i, j, 1] for j in tdwms_idx_list)
                    )
                else:
                    mdl_cost.add_constraint(
                        yid[i, d] * (Wi[i]/ti[i]) + rid[i, d-1]
                        == rid[i, d] + mdl_cost.sum(zijd[i, j, d] for j in tdwms_idx_list)
                    )

        for i in customer_idx_list:
            mdl_cost.add_constraint(rid[i, T_last] == 0)

        for i in customer_idx_list:
            for j in tdwms_idx_list:
                for d in range(1, T_last+1):
                    mdl_cost.add_constraint(zijd[i, j, d] <= aijd[i, j, d] * Q)

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(aijd[x, y, d] * (uij[(x, y)]/v) * 60
                            for x in range(n_total) for y in range(n_total))
                <= len(K)*R
            )

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(aijd[depot_idx, i, d] for i in customer_idx_list)
                == mdl_cost.sum(aijd[j, depot_idx, d] for j in tdwms_idx_list)
            )

        for i in customer_idx_list:
            for d in range(1, T_last+1):
                mdl_cost.add_constraint(
                    mdl_cost.sum(aijd[x, i, d] for x in [depot_idx]+tdwms_idx_list)
                    == mdl_cost.sum(aijd[i, y, d] for y in [depot_idx]+tdwms_idx_list)
                )

        for j in tdwms_idx_list:
            for d in range(1, T_last+1):
                mdl_cost.add_constraint(
                    mdl_cost.sum(aijd[x, j, d] for x in [depot_idx]+customer_idx_list)
                    == mdl_cost.sum(aijd[j, y, d] for y in [depot_idx]+customer_idx_list)
                )

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(aijd[depot_idx, i, d] for i in customer_idx_list) <= len(K)
            )

        for i in customer_idx_list:
            mdl_cost.add_constraint(
                mdl_cost.sum(zijd[i, j, d] for j in tdwms_idx_list for d in range(1, T_last+1)) == Wi[i]
            )

        for j in tdwms_idx_list:
            for d in range(0, T_last+1):
                if d == 0:
                    mdl_cost.add_constraint(rjd[j, 0] == 0)
                else:
                    mdl_cost.add_constraint(
                        (1-g)*mdl_cost.sum(zijd[i, j, d] for i in customer_idx_list)
                        + rjd[j, d-1]
                        == rjd[j, d] + mdl_cost.sum(fjld[j, f, d] for f in final_idx_list)
                    )

        for j in tdwms_idx_list:
            mdl_cost.add_constraint(rjd[j, T_last] == 0)

        for j in tdwms_idx_list:
            for f in final_idx_list:
                for d in range(1, T_last+1):
                    mdl_cost.add_constraint(fjld[j, f, d] <= bjld[j, f, d]*Q0)

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(bjld[x, y, d] * (uij[(x, y)]/v0)*60
                            for x in range(n_total) for y in range(n_total))
                <= len(K0)*R
            )

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(aijd[depot_idx, i, d] for i in customer_idx_list + tdwms_idx_list) >= 1
            )

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(bjld[depot_idx, j, d] for j in tdwms_idx_list)
                == mdl_cost.sum(bjld[f, depot_idx, d] for f in final_idx_list)
            )

        for j in tdwms_idx_list:
            for d in range(1, T_last+1):
                mdl_cost.add_constraint(
                    mdl_cost.sum(bjld[x, j, d] for x in final_idx_list+[depot_idx])
                    == mdl_cost.sum(bjld[j, y, d] for y in final_idx_list+[depot_idx])
                )

        for f in final_idx_list:
            for d in range(1, T_last+1):
                mdl_cost.add_constraint(
                    mdl_cost.sum(bjld[x, f, d] for x in tdwms_idx_list+[depot_idx])
                    == mdl_cost.sum(bjld[f, x, d] for x in tdwms_idx_list+[depot_idx])
                )

        for d in range(1, T_last+1):
            mdl_cost.add_constraint(
                mdl_cost.sum(bjld[depot_idx, j, d] for j in tdwms_idx_list) <= len(K0)
            )

        for j in tdwms_idx_list:
            for d in range(0, T_last+1):
                mdl_cost.add_constraint(rjd[j, d] <= xj[j]*sj[j])

        mdl_cost.add_constraint(
            (1-g)*mdl_cost.sum(zijd[i, j, d]
                            for i in customer_idx_list for j in tdwms_idx_list for d in range(1, T_last+1))
            == mdl_cost.sum(fjld[j, f, d]
                        for j in tdwms_idx_list for f in final_idx_list for d in range(1, T_last+1))
        )

        for d in range(1, T_last+1):
            for i in customer_idx_list:
                mdl_cost.add_constraint(sd[d] >= 1 - cid[i, d]/Wi[i])
            for j in tdwms_idx_list:
                mdl_cost.add_constraint(sd[d] >= 1 - rjd[j, d]/sj[j])

        for j in tdwms_idx_list:
            mdl_cost.add_constraint(
                lj[j] <= ((T_last+1)-mdl_cost.sum(sd[d] for d in range(T_last+1))+1)*Oj[j]
                        + (T_last+1)*Oj[j]*(1 - xj[j])
            )

        # Add a constraint to fix the total clean-up time
        mdl_cost.add_constraint(mdl_cost.sum(sd[d] for d in range(1, T_last + 1)) <= optimal_time + 1)  # Small tolerance

        # Objective: Minimize total cost
        totalEstablishmentCost = mdl_cost.sum(xj[j] * Ej[j] for j in tdwms_idx_list)
        totalTdwmsOperation = mdl_cost.sum(lj[j] for j in tdwms_idx_list)

        totalCollectionCost = mdl_cost.sum(
            mdl_cost.sum(aijd[depot_idx, i, d] * uij[(depot_idx, i)] * ck for i in customer_idx_list)
            + mdl_cost.sum(aijd[i, j, d] * uij[(i, j)] * ck for i in customer_idx_list for j in tdwms_idx_list)
            + mdl_cost.sum(aijd[j, depot_idx, d] * uij[(j, depot_idx)] * ck for j in tdwms_idx_list)
            for d in range(1, T_last+1)
        )

        totalTransportCost = mdl_cost.sum(
            mdl_cost.sum(bjld[depot_idx, j, d] * uij[(depot_idx, j)] * ck0 for j in tdwms_idx_list)
            + mdl_cost.sum(bjld[j, f, d] * uij[(j, f)] * ck0 for j in tdwms_idx_list for f in final_idx_list)
            + mdl_cost.sum(bjld[f, depot_idx, d] * uij[(f, depot_idx)] * ck0 for f in final_idx_list)
            for d in range(1, T_last+1)
        )

        totalCost = totalEstablishmentCost + totalTdwmsOperation + totalCollectionCost + totalTransportCost
        mdl_cost.minimize(totalCost)

        # Solve the model
        print(">>> Solving Stage 2: Minimizing Cost...")
        solution_cost = mdl_cost.solve(log_output=True)
        if solution_cost:
            optimal_cost = solution_cost.objective_value
            print("Optimal Cost:", optimal_cost)
        else:
            print("No solution found for cost minimization.")
            return

        # Collect usage data
        usage_data = {}

        # First echelon (depot -> customer/tdwms)
        for x in range(n_total):
            for y in range(n_total):
                total_flow = sum(aijd[x, y, d].solution_value for d in range(1, T_last + 1))
                if total_flow > 0:  # Only add and print flows greater than zero
                    usage_data[(x, y)] = total_flow
                    print(f"Flow from {x} to {y}: {total_flow}")

        # Second echelon (tdwms -> final)
        for x in range(n_total):
            for y in range(n_total):
                total_flow = sum(bjld[x, y, d].solution_value for d in range(1, T_last + 1))
                if total_flow > 0:  # Only add and print flows greater than zero
                    usage_data[(x, y)] = total_flow
                    print(f"Flow from {x} to {y}: {total_flow}")

        # Draw and save the heatmap
        self.draw_heatmap(usage_data, all_points)
        messagebox.showinfo("Heatmap", "The heatmap has been saved as heatmap.png!")

        self.model_solution_text += "\n--- MODEL SOLUTION RESULTS ---\n"
        self.model_solution_text += f"Optimal Time: {optimal_time}\n"
        self.model_solution_text += f"Optimal Cost: {optimal_cost}\n"

        self.usage_data = usage_data

        # File name (solution_output_1.txt, solution_output_2.txt, ...)
        base_name = "solution_output_"
        file_index = 1
        while True:
            candidate_name = f"{base_name}{file_index}.txt"
            candidate_path = os.path.join(RESULTS_FOLDER, candidate_name)
            if not os.path.exists(candidate_path):
                break
            file_index += 1

        sol_path = candidate_path
        with open(sol_path, "w", encoding="utf-8") as f:
            f.write(self.model_solution_text)

        msg = f"{self.model_solution_text}\nFile: {os.path.basename(sol_path)}"
        messagebox.showinfo("Model Solution", msg)

    def show_results(self):
        """Enhanced results window"""
        w = tk.Toplevel(self.root)
        w.title("Analysis Results")
        w.geometry("800x600")
        
        # Apply same theme
        sv_ttk.set_theme("dark")
        
        # Create frames with better styling
        frame_list = ttk.Frame(w)
        frame_list.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        frame_text = ttk.Frame(w)
        frame_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Enhanced listbox
        ttk.Label(frame_list, text="📄 Available Reports", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        lb = tk.Listbox(
            frame_list,
            width=30,
            bg='#2d2d2d',
            fg='white',
            font=('Segoe UI', 10),
            selectmode=tk.SINGLE,
            relief=tk.FLAT,
            borderwidth=0
        )
        lb.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        scrollbar = tk.Scrollbar(frame_list, orient="vertical", command=lb.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lb.config(yscrollcommand=scrollbar.set)

        text_box = tk.Text(frame_text, wrap="word")
        text_box.pack(fill=tk.BOTH, expand=True)

        pattern = os.path.join(RESULTS_FOLDER, "*.txt")
        txt_files = glob.glob(pattern)
        txt_files.sort()

        for file_path in txt_files:
            lb.insert(tk.END, os.path.basename(file_path))

        def open_selected_file(event):
            selection = lb.curselection()
            if not selection:
                return
            selected_file = lb.get(selection[0])
            full_path = os.path.join(RESULTS_FOLDER, selected_file)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            text_box.config(state=tk.NORMAL)
            text_box.delete("1.0", tk.END)
            text_box.insert("1.0", f"=== {selected_file} ===\n\n{content}")
            text_box.config(state=tk.DISABLED)

        lb.bind("<<ListboxSelect>>", open_selected_file)

    def show_old_heatmaps(self):
        """Enhanced heatmaps window"""
        w = tk.Toplevel(self.root)
        w.title("Historical Heatmaps")
        w.geometry("1000x700")
        
        # Apply same theme
        sv_ttk.set_theme("dark")
        
        # Create frames with better styling
        frame_list = ttk.Frame(w)
        frame_list.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        frame_image = ttk.Frame(w)
        frame_image.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Enhanced listbox
        ttk.Label(frame_list, text="🗺️ Saved Heatmaps", style='Header.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        lb = tk.Listbox(
            frame_list,
            width=30,
            bg='#2d2d2d',
            fg='white',
            font=('Segoe UI', 10),
            selectmode=tk.SINGLE,
            relief=tk.FLAT,
            borderwidth=0
        )
        lb.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        scrollbar = tk.Scrollbar(frame_list, orient="vertical", command=lb.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lb.config(yscrollcommand=scrollbar.set)

        # Create a label to display the heatmap
        image_label = tk.Label(frame_image)
        image_label.pack(fill=tk.BOTH, expand=True)

        # Get all heatmap files
        pattern = os.path.join(RESULTS_FOLDER, "heatmap_*.png")
        heatmap_files = glob.glob(pattern)
        heatmap_files.sort(reverse=True)  # Most recent first

        for file_path in heatmap_files:
            lb.insert(tk.END, os.path.basename(file_path))

        def show_selected_heatmap(event):
            selection = lb.curselection()
            if not selection:
                return
                
            selected_file = lb.get(selection[0])
            full_path = os.path.join(RESULTS_FOLDER, selected_file)
            
            try:
                # Load and resize image to fit the window
                image = Image.open(full_path)
                # Calculate new size while maintaining aspect ratio
                display_size = (700, 500)
                image.thumbnail(display_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                # Update label with new image
                image_label.config(image=photo)
                image_label.image = photo  # Keep a reference
            except Exception as e:
                messagebox.showerror("Error", f"Could not load heatmap: {str(e)}")

        lb.bind("<<ListboxSelect>>", show_selected_heatmap)

def main():
    root = ThemedTk(theme="black")
    root.tk.call('tk', 'scaling', 1.3)
    app = MapGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()