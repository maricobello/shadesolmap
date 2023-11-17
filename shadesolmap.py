#app2
import streamlit as st
import requests
import numpy as np
from io import BytesIO
from PIL import Image
from rasterio.io import MemoryFile
import matplotlib.pyplot as plt

# Adição da descrição inicial e imagem
st.sidebar.markdown("<h1 style='text-align: center;'>SHADESOLMAP</h1>", unsafe_allow_html=True)
st.sidebar.image("https://i.imgur.com/FcnKBrU.jpg", use_column_width=True)

# Adição da barra lateral com descrição e link para o LinkedIn
st.sidebar.markdown("Visualize uma imagem do fluxo médio anual de luz solar em seu local, seguida por 12 imagens detalhadas, representando o fluxo solar mês a mês. Tudo isso com base em dados precisos da API Google Solar.", unsafe_allow_html=True)
st.sidebar.markdown("<h2 style='text-align: center;'>Desenvolvido por Matheus Ricobello</h2>", unsafe_allow_html=True)
st.sidebar.write("--------[LinkedIn](https://www.linkedin.com/in/matheus-ricobello/)", unsafe_allow_html=True)

GOOGLE_SOLAR_KEY = "AIzaSyAuDJhWd_YIrSPXA8lg-Oe75behxSzeDM4"
SOLAR_INSIGHTS_ENDPOINT = 'https://solar.googleapis.com/v1/buildingInsights:findClosest?location.latitude={}&location.longitude={}&requiredQuality=LOW&key={}'

@st.cache_data
def get_lat_lng(address):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GOOGLE_SOLAR_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            return data['results'][0]['geometry']['location']['lat'], data['results'][0]['geometry']['location']['lng']
    return None, None

@st.cache_data
def get_solar_insights(lat, lng):
    response = requests.get(SOLAR_INSIGHTS_ENDPOINT.format(lat, lng, GOOGLE_SOLAR_KEY))
    return response.json()

@st.cache_data
def get_google_maps_image(lat, lon, zoom=19, size="600x600", maptype="satellite", api_key=GOOGLE_SOLAR_KEY):
    base_url = "https://maps.googleapis.com/maps/api/staticmap?"
    params = {
        "center": f"{lat},{lon}",
        "zoom": zoom,
        "size": size,
        "maptype": maptype,
        "key": api_key
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    return image

@st.cache_data
def get_data_layers(lat, lon, radius=50, view="FULL_LAYERS", quality="LOW", pixel_size=0.5):
    url = f"https://solar.googleapis.com/v1/dataLayers:get"
    params = {
        "location.latitude": lat,
        "location.longitude": lon,
        "radiusMeters": radius,
        "view": view,
        "requiredQuality": quality,
        "pixelSizeMeters": pixel_size,
        "key": GOOGLE_SOLAR_KEY
    }
    response = requests.get(url, params=params)
    return response.json()

def display_all_geotiff_bands(url, api_key, title):
    url_with_key = f"{url}&key={api_key}"
    response = requests.get(url_with_key)
    if response.status_code == 200:
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset:
                fig, ax = plt.subplots()
                if dataset.count > 1:
                    band = dataset.read([1, 2, 3])
                    band = np.transpose(band, (1, 2, 0))
                else:
                    band = dataset.read(1)
                    band = band.squeeze()

                im = ax.imshow(band)
                ax.set_title(title)
                st.pyplot(fig)
                plt.close(fig)
    else:
        print(f"Falha ao buscar dados. Codigo de status: {response.status_code}")

# Function to display a specific band of a GeoTIFF file from a URL with annotation
def display_monthly_flux(data_layers, api_key):
    # For monthly flux, you need to handle multiple bands as it contains data for each month
    monthly_flux_url_with_key = f"{data_layers['monthlyFluxUrl']}&key={api_key}"
    response = requests.get(monthly_flux_url_with_key)
    if response.status_code == 200:
        with MemoryFile(response.content) as memfile:
            with memfile.open() as dataset:
                for i in range(1, dataset.count + 1):  # Loop through each band
                    fig, ax = plt.subplots()  # Create a new matplotlib figure and axes
                    band = dataset.read(i)
                    im = ax.imshow(band) #cmap='viridis')  # Store the mappable object in im
                    #plt.colorbar(im, ax=ax)  # Pass the mappable object to colorbar
                    ax.set_title(f"Fluxo Solar Mensal - Mês {i}")
                    st.pyplot(fig)  # Pass the matplotlib figure to st.pyplot()
                    plt.close(fig)  # Close the figure
    else:
        print(f"Falha ao buscar dados. Codigo de status: {response.status_code}")

def main():
    st.title('Consulta de Sombreamento e Dados Solares')

    address = st.text_input("Digite seu endereço:")

    if st.button('Obter Dados Solares'):
        lat, lng = get_lat_lng(address)
        data_layers = get_data_layers(lat, lng)

        st.subheader('Imagem do Local')
        house_image = get_google_maps_image(lat, lng)
        st.image(house_image, caption="Imagem do Local", use_column_width=True)

        st.write("<h2 style='text-align: center;'>Fluxo anual de incidência solar média.</h2>", unsafe_allow_html=True)
        display_all_geotiff_bands(data_layers['annualFluxUrl'], GOOGLE_SOLAR_KEY, 'Fluxo Anual')

        st.write("<h2 style='text-align: center;'>Fluxo mensal de incidência solar mês a mês.</h2>", unsafe_allow_html=True)
        display_monthly_flux(data_layers, GOOGLE_SOLAR_KEY)

        st.write("<h2 style='text-align: center;'>Modelo digital da superfície, com dados da topografia local.</h2>", unsafe_allow_html=True)
        display_all_geotiff_bands(data_layers['dsmUrl'], GOOGLE_SOLAR_KEY, 'Superfície do local digitalizada')

        st.write("<h2 style='text-align: center;'>Camada RGB sólida.</h2>", unsafe_allow_html=True)
        display_all_geotiff_bands(data_layers['rgbUrl'], GOOGLE_SOLAR_KEY, 'Camada RGB do local')

        st.write("<h2 style='text-align: center;'>Modelo de identificação de estruturas.</h2>", unsafe_allow_html=True)
        display_all_geotiff_bands(data_layers['maskUrl'], GOOGLE_SOLAR_KEY, 'Layer de estruturas')

if __name__ == '__main__':
    main()
