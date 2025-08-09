import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import numpy as np
import plotly.express as px

# --------------------------------------------------------------------------------------------
# Page config + styles
# --------------------------------------------------------------------------------------------
st.set_page_config(page_title="Marvelpious | MTA Art Map", page_icon="🗽", layout="wide")
st.markdown(
    """
    <style>
      /* Sidebar: slightly darker navy */
      [data-testid="stSidebar"] { background-color: #0A2540; color: #fff; }

      /* Main page background: slightly lighter dark blue */
      .main { background-color: #1A2B47; }

      /* Headings text color (not the table) */
      h2, h3 { color: #8AAAF0 !important; family="Arial Black"}

      /* Button color */
      .stButton>button { background-color: #0B3D91; color: black; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------------------------
# Load & clean data
# --------------------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(path="station_coords.csv"):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    if "lat" in df.columns and "lon" in df.columns:
        df = df.rename(columns={"lat": "latitude", "lon": "longitude"})
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    for c in ["agency", "station_name", "artist", "artwork_title"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
        else:
            df[c] = "Unknown"
    if "art_date" in df.columns:
        df["year"] = df["art_date"].astype(str).str.extract(r"(\d{4})")[0]
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Float64")
    else:
        df["year"] = pd.NA
    df = df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    return df
import pandas as pd

url = "week29/station_coords.csv"
df = pd.read_csv(url)


# --------------------------------------------------------------------------------------------
# Sidebar filters
# --------------------------------------------------------------------------------------------
st.sidebar.header("Filters")
agencies = sorted(df["agency"].dropna().unique())
selected_agency = st.sidebar.selectbox("Agency", ["All"] + agencies)

years_valid = df["year"].dropna().astype(int) if not df["year"].isna().all() else pd.Series([], dtype=int)
if not years_valid.empty:
    min_year = int(years_valid.min())
    max_year = int(years_valid.max())
    if min_year == max_year:
        min_year -= 1
        max_year += 1
    default_start = int(years_valid.min())
    default_end = int(years_valid.max())
else:
    min_year, max_year = 1900, 2025
    default_start, default_end = min_year, max_year

selected_year_range = st.sidebar.slider(
    "Art year range",
    min_value=min_year,
    max_value=max_year,
    value=(default_start, default_end),
)

# --------------------------------------------------------------------------------------------
# Apply filters
# --------------------------------------------------------------------------------------------
filtered_df = df.copy()
if selected_agency != "All":
    filtered_df = filtered_df[filtered_df["agency"] == selected_agency].copy()

if "year" in filtered_df.columns:
    filtered_df["year_int"] = pd.to_numeric(filtered_df["year"], errors="coerce").astype("Float64")
    filtered_df = filtered_df[
        (filtered_df["year_int"] >= selected_year_range[0]) & (filtered_df["year_int"] <= selected_year_range[1])
    ].copy()
    filtered_df.drop(columns=["year_int"], inplace=True, errors="ignore")
filtered_df["latitude"] = pd.to_numeric(filtered_df["latitude"], errors="coerce")
filtered_df["longitude"] = pd.to_numeric(filtered_df["longitude"], errors="coerce")
filtered_df = filtered_df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

# --------------------------------------------------------------------------------------------
# Layout: map (left) + table (right)
# --------------------------------------------------------------------------------------------
col_map, col_table = st.columns([2, 1])
with col_map:
    st.subheader("Interactive map")
    if filtered_df.empty:
        st.info("No results to display for the selected filters.")
    else:
        center_lat = filtered_df["latitude"].mean()
        center_lon = filtered_df["longitude"].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")
        marker_cluster = MarkerCluster()
        for _, row in filtered_df.iterrows():
            popup_html = (
                f"<b>{row.get('artwork_title','Unknown')}</b><br>"
                f"{row.get('artist','')}<br>"
                f"<b>Station:</b> {row.get('station_name','')}<br>"
                f"<b>Year:</b> {row.get('art_date','')}<br>"
                f"<b>Material:</b> {row.get('art_material','')}<br>"
                f"<a href='{row.get('link','')}' target='_blank'>View artwork</a>"
            )
            folium.Marker(
                location=[row["latitude"], row["longitude"]],
                popup=popup_html,
                tooltip=row.get("station_name", ""),
                icon=folium.Icon(icon="bolt", prefix='fa', color="lightblue")
            ).add_to(marker_cluster)
        marker_cluster.add_to(m)
        map_out = st_folium(m, width=900, height=700)
with col_table:
    st.subheader("Filtered data")
    visible_df = filtered_df.copy()
    if isinstance(locals().get("map_out"), dict) and map_out:
        bounds = map_out.get("bounds")
        if bounds and isinstance(bounds, list) and len(bounds) == 2:
            sw, ne = bounds 
            sw_lat, sw_lng = sw[0], sw[1]
            ne_lat, ne_lng = ne[0], ne[1]
            visible_df = visible_df[
                (visible_df["latitude"] >= sw_lat)
                & (visible_df["latitude"] <= ne_lat)
                & (visible_df["longitude"] >= sw_lng)
                & (visible_df["longitude"] <= ne_lng)
            ].copy()
    if visible_df.empty:
        st.info("No points currently visible on the map (or bounds unavailable). Showing filtered dataset instead.")
        visible_df = filtered_df
    display_cols = [
        c for c in ["agency", "station_name", "artwork_title", "artist", "art_date", "art_material", "link"]
        if c in visible_df.columns
    ]
    st.write(f"Showing {len(visible_df)} row(s)")
    st.dataframe(visible_df[display_cols].reset_index(drop=True), use_container_width=True)


# --------------------------------------------------------------------------------------------
# Line chart of artworks over years (below map and table)
# --------------------------------------------------------------------------------------------
year_data = (
    filtered_df.dropna(subset=["year"])
    .copy()
)
if not year_data.empty:
    year_counts = (
        year_data.groupby("year").size().reset_index(name="count")
    )
    jitter_strength = 0.2
    year_data["year_jitter"] = year_data["year"] + np.random.uniform(-jitter_strength, jitter_strength, size=len(year_data))
    fig = px.scatter(
        year_data,
        x="year_jitter",
        y=[1]*len(year_data),  
        hover_name="artist",
        hover_data={
            "artwork_title": True,
            "year": True,
            "year_jitter": False,
        },
        labels={"year_jitter": "Year"},
        title="Artworks Over Time (Artist & Title on Hover)",
        template="plotly_dark",
        color_discrete_sequence=["#8AAAF0"]
    )
    max_count = year_counts["count"].max()
    scaled_counts = year_counts["count"] / max_count * 0.8
    fig.add_scatter(
        x=year_counts["year"],
        y=scaled_counts,
        mode="lines+markers",
        name="Artwork count",
        line=dict(color="#8AAAF0", width=3),
        marker=dict(size=8, color="#8AAAF0"),
        yaxis="y2",
    )
    fig.update_layout(
        dragmode="pan",
        hovermode="closest",
        xaxis=dict(
            title="Year",
            dtick=5,
            showgrid=True,
            zeroline=False,
            showspikes=True,
            spikecolor="#8AAAF0",
            spikesnap="cursor",
            spikemode="across",
        ),
        yaxis=dict(
            visible=False,
        ),
        yaxis2=dict(
            overlaying='y',
            side='right',
            showgrid=False,
            zeroline=False,
            range=[0, 1],
            title="Count (scaled)",
            color="#8AAAF0",
        ),
        font=dict(family="Arial", size=14, color="#4B73D9"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=20, family="Arial Black", color="#8AAAF0"),
        legend=dict(font=dict(color="#8AAAF0")),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No artwork year data available for the selected filters.")
