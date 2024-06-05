import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Configuración de las credenciales y acceso a la Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Abre la Google Sheet
sheet = client.open("keys_database").sheet1  # Cambia "Nombre de tu Google Sheet" por el nombre de tu hoja

# Lee todos los datos de la hoja
data = sheet.get_all_records()

# Interfaz de usuario en Streamlit
st.title("Aplicación de Ejemplo con Google Sheets")
st.write("Datos leídos desde Google Sheets:")
st.write(data)

# Sección para ingresar nuevos datos
st.write("Añadir nuevos datos a la Google Sheet:")
name = st.text_input("Nombre:")
age = st.number_input("Edad:", min_value=0, step=1)
city = st.text_input("Ciudad:")

if st.button("Añadir a la Google Sheet"):
    # Verifica que los campos no estén vacíos
    if name and age and city:
        new_row = [name, age, city]
        sheet.append_row(new_row)
        st.success("Datos añadidos exitosamente a la Google Sheet.")
        # Actualiza los datos mostrados
        data = sheet.get_all_records()
        st.write(data)
    else:
        st.error("Por favor, completa todos los campos.")


