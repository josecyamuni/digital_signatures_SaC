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

# Configuración de la base de datos
engine = db.create_engine('sqlite:///keys.db')
metadata = db.MetaData()

# Definir la tabla 'keys'
keys = db.Table('keys', metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('email', db.String, nullable=False, unique=True),
    db.Column('comment', db.String, nullable=False),
    db.Column('key_id', db.String, nullable=False, unique=True)  # Se agrega la columna para el key_id
)

# Crear la tabla en la base de datos
metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# Función para agregar una clave pública a la base de datos
def add_public_key(email, key_id, comment):
    new_key = keys.insert().values(email=email, key_id=key_id, comment=comment)
    session.execute(new_key)
    session.commit()
    
def delete_public_key(email, comment):
    key_to_delete = keys.delete().where(keys.c.email == email, keys.c.comment == comment)
    result = session.execute(key_to_delete)
    if result.rowcount == 0:
        return False
    session.commit()
    return True

# Función para obtener el key_id asociado a un correo
def get_key_id(email):
    key_record = session.query(keys).filter(keys.c.email == email).first()
    if key_record:
        return key_record.key_id
    else:
        return None

# Función para firmar el documento
def sign_document(document_data, key_id):
    gpg = gnupg.GPG()
    
    if not key_id:
        return None, 'No se encontró el key_id asociado al correo proporcionado.'
    
    # Firmar el documento
    signature = gpg.sign(document_data, keyid=key_id)
    
    # Devolver la firma
    return signature.data, None

# Función para verificar el documento firmado
def verify_document(signed_data, email):
    gpg = gnupg.GPG()
    
    key_id = get_key_id(email)
    if not key_id:
        return False, 'No hay una llave pública asignada al correo ingresado.'
    
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
            key_id = key_id
            if key_id:
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
                st.error('No se encontró el key_id asociado al correo proporcionado.')
        else:
            st.error('Por favor, proporciona el archivo y el correo asociado.')

elif sidebar_option == 'Verificar documento':
    st.subheader('Verificar documento')
    email = st.text_input('Ingrese el correo de la persona que firmó el documento')
    uploaded_file = st.file_uploader('Selecciona el archivo firmado')

    if st.button('Verificar documento'):
        if uploaded_file and email:
            signed_data = uploaded_file.read()
            verified, message = verify_document(signed_data, email)
            if verified:
                st.success(message)
            else:
                st.error(message)
        else:
            st.error('Por favor, selecciona un archivo y proporciona el correo asociado.')

elif sidebar_option == 'Añadir llave pública':
    st.subheader('Añadir llave pública')
    email_input = st.text_input('Ingresa el correo asociado a la llave')
    key_id_input = st.text_input('Ingresa el key_id asociado a la llave')
    comment_input = st.text_input('Ingresa el comentario asociado la llave')
    
    if st.button('Añadir'):
        if email_input and key_id_input and comment_input:
            add_public_key(email_input, key_id_input, comment_input)
            st.success('Llave pública cargada correctamente.')
        else:
            st.error('Por favor, proporciona el correo, el key_id y el comentario.')

# Agrega una opción para eliminar la llave pública en la barra lateral
elif sidebar_option == 'Eliminar llave pública':
    st.subheader('Eliminar llave pública')
    email_to_delete = st.text_input('Ingresa el correo asociado a la llave que deseas eliminar')
    comment_to_delete = st.text_input('Ingresa el comentario asociado a la llave que deseas eliminar')

    if st.button('Eliminar'):
        if email_to_delete and comment_to_delete:
            if delete_public_key(email_to_delete, comment_to_delete):
                st.success('Llave pública eliminada correctamente.')
            else:
                st.error('No se encontró ninguna llave pública con el correo y comentario proporcionados.')
        else:
            st.error('Por favor, proporciona el correo y el comentario asociados a la llave que deseas eliminar.')