# -*- coding: utf-8 -*-
"""
Created on Mon May 27 07:59:44 2024

@author: Equipo 2
"""

import gnupg
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import io
from PIL import Image

# Configuración de las credenciales y acceso a la Google Sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Abre la Google Sheet
sheet = client.open("keys_database").sheet1

# Función para agregar una clave pública a la base de datos
def add_public_key(email, key_id, comment):
    existing_records = sheet.get_all_records()
    new_id = len(existing_records) + 1  # Genera un nuevo ID
    new_key = [new_id, email.lower(), comment.lower(), key_id]
    sheet.append_row(new_key)

# Función para eliminar una clave pública de la base de datos
def delete_public_key(email, comment):
    cells = sheet.findall(email.lower())
    for cell in cells:
        row = cell.row
        row_values = sheet.row_values(row)
        if row_values[2] == comment.lower():  # Verifica si el comentario coincide
            sheet.delete_rows(row)
            return True
    return False

# Función para obtener el key_id y la clave pública asociada a un comentario
def get_key_id_by_comment(comment):
    records = sheet.get_all_records()
    for record in records:
        if record['comment'] == comment.lower():
            return record['key_id'], record['public_key']
    return None, None

# Función para exportar la clave pública y guardarla en la base de datos
def export_and_store_public_key(email, key_id, comment):
    gpg = gnupg.GPG()
    public_key = gpg.export_keys(key_id)
    if not public_key:
        return False, 'Error al exportar la clave pública.'

    add_public_key(email, key_id, comment)
    return True, 'Clave pública exportada y guardada correctamente.'

# Función para firmar el documento
def sign_document(document_data, key_id):
    gpg = gnupg.GPG()
    if not key_id:
        return None, 'No se encontró el key_id asociado al comentario proporcionado.'

    # Firmar el documento
    signature = gpg.sign(document_data, keyid=key_id)
    
    # Devolver la firma
    return signature.data, None

# Función para verificar el documento firmado
def verify_document(signed_data, comment):
    gpg = gnupg.GPG()
    key_id, public_key = get_key_id_by_comment(comment)
    
    if not key_id:
        return False, 'No hay una llave pública asignada al comentario ingresado.'

    # Verificar si la clave ya está en el llavero
    if not any(key['keyid'] == key_id for key in gpg.list_keys()):
        # Importar la clave pública
        import_result = gpg.import_keys(public_key)
        if import_result.count == 0:
            return False, 'Error al importar la llave pública.'

    # Verificar la firma
    verified = gpg.verify(signed_data)
    
    return verified, 'Firma verificada: el documento es auténtico.' if verified else 'Firma no verificada: el documento no es auténtico.'

# Interfaz de Streamlit
st.title('Documento Seguro: Firmado y verificación de documentos')
st.subheader('Sigue al Congreso')

imagen_original = Image.open("images/logo.jpg")
# Redimensiona la imagen
nuevo_ancho = 200  # Define el nuevo ancho
nuevo_alto = int((nuevo_ancho / imagen_original.width) * imagen_original.height)  # Mantén la proporción
imagen_redimensionada = imagen_original.resize((nuevo_ancho, nuevo_alto))
st.image(imagen_redimensionada)

st.caption('Bienvenido a Documento Seguro, una aplicación avanzada diseñada para firmar y validar documentos electrónicamente, asegurando la autenticidad e integridad de la información contenida. Con esta app, los usuarios de Sigue al congreso pueden aplicar firmas digitales a sus documentos que garantiza que el contenido no ha sido alterado desde su firma. La aplicación utiliza tecnología de cifrado robusta, compatible con estándares de seguridad globales, para ofrecer una solución confiable tanto para individuos como para empresas que buscan proteger sus documentos sensibles.')

# Crear una barra lateral para las opciones
sidebar_option = st.sidebar.radio('Opciones', ('Firmar documento', 'Verificar documento', 'Añadir llave pública', 'Eliminar llave pública'))

# Opciones de la barra lateral
if sidebar_option == 'Firmar documento':
    st.subheader('Firmar documento')
    key_id = st.text_input('Ingrese su key_id de su clave privada')
    uploaded_file = st.file_uploader('Selecciona el archivo que deseas firmar')
    
    if st.button('Firmar'):
        if uploaded_file and key_id:
            document_data = uploaded_file.read()
            signed_data, error = sign_document(document_data, key_id)
            if error:
                st.error(error)
            else:
                signed_file = io.BytesIO(signed_data)
                signed_file_name = uploaded_file.name + '.asc'
                st.download_button(
                    label='Descargar documento firmado',
                    data=signed_file,
                    file_name=signed_file_name,
                    mime='application/pgp-signature'
                )
        else:
            st.error('Por favor, proporciona el archivo y la llave privada.')

elif sidebar_option == 'Verificar documento':
    st.subheader('Verificar documento')
    comment = st.text_input('Ingrese el usuario del propietario de la clave pública')
    uploaded_file = st.file_uploader('Selecciona el archivo firmado')

    if st.button('Verificar documento'):
        if uploaded_file and comment:
            signed_data = uploaded_file.read()
            verified, message = verify_document(signed_data, comment)
            if verified:
                st.success(message)
            else:
                st.error(message)
        else:
            st.error('Por favor, selecciona un archivo y proporciona el usuario del propietario de la clave pública.')

elif sidebar_option == 'Añadir llave pública':
    st.subheader('Añadir llave pública')
    comment_input = st.text_input('Ingresa el comentario (usuario) asociado a la llave').lower()
    key_id_input = st.text_input('Ingresa el key_id público asociado a la llave')
    email_input = st.text_input('Ingresa el correo asociado la llave').lower()
    
    if st.button('Añadir'):
        if email_input and key_id_input and comment_input:
            success, message = export_and_store_public_key(email_input, key_id_input, comment_input)
            if success:
                st.success(message)
            else:
                st.error(message)
        else:
            st.error('Por favor, proporciona el correo, el key_id y el comentario.')

elif sidebar_option == 'Eliminar llave pública':
    st.subheader('Eliminar llave pública')
    comment_to_delete = st.text_input('Ingresa el comentario (usuario) asociado a la llave que deseas eliminar').lower()
    email_to_delete = st.text_input('Ingresa el correo asociado a la llave que deseas eliminar').lower()

    if st.button('Eliminar'):
        if comment_to_delete and email_to_delete:
            if delete_public_key(email_to_delete, comment_to_delete):
                st.success('Llave pública eliminada correctamente.')
            else:
                st.error('No se encontró ninguna llave pública con el correo y comentario proporcionados.')
        else:
            st.error('Por favor, proporciona el correo y el comentario asociados a la llave que deseas eliminar.')
