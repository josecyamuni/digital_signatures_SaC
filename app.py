# -*- coding: utf-8 -*-
"""
Created on Mon May 27 07:59:44 2024

@author: Equipo 2
"""

import gnupg
import streamlit as st
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
import io
import requests

# Configuración de GPG
gpg = gnupg.GPG()

# Configuración de la base de datos
engine = db.create_engine('sqlite:///keys.db')
metadata = db.MetaData()

# Definir la tabla 'keys'
keys = db.Table('keys', metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('email', db.String, nullable=False, unique=True),
    db.Column('comment', db.String, nullable=False),
    db.Column('key_id', db.String, nullable=False, unique=True),  # Se agrega la columna para el key_id
    db.Column('public_key', db.Text, nullable=False)  # Columna para almacenar la clave pública
)

# Crear la tabla en la base de datos
metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# Función para exportar la clave pública y guardarla en la base de datos
def export_and_store_public_key(email, key_id, comment):
    public_key = gpg.export_keys(key_id)
    if not public_key:
        return False, 'Error al exportar la clave pública.'

    new_key = keys.insert().values(email=email.lower(), key_id=key_id, comment=comment.lower(), public_key=public_key)
    session.execute(new_key)
    session.commit()
    return True, 'Clave pública exportada y guardada correctamente.'

# Función para eliminar una clave pública de la base de datos
def delete_public_key(email, comment):
    key_to_delete = keys.delete().where(keys.c.email == email.lower(), keys.c.comment == comment.lower())
    result = session.execute(key_to_delete)
    if result.rowcount == 0:
        return False
    session.commit()
    return True

# Función para obtener el key_id y la clave pública asociada a un comentario
def get_key_id_by_comment(comment):
    key_record = session.query(keys).filter(keys.c.comment == comment.lower()).first()
    if key_record:
        return key_record.key_id, key_record.public_key
    else:
        return None, None

# Función para firmar el documento
def sign_document(document_data, key_id):
    if not key_id:
        return None, 'No se encontró el key_id asociado al comentario proporcionado.'

    # Firmar el documento
    signature = gpg.sign(document_data, keyid=key_id)
    
    # Devolver la firma
    return signature.data, None

# Función para verificar el documento firmado
def verify_document(signed_data, comment):
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
st.subheader('Sigue al congreso')

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
    comment = st.text_input('Ingrese el comentario del propietario de la clave pública')
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
            st.error('Por favor, selecciona un archivo y proporciona el comentario del propietario de la clave pública.')

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
