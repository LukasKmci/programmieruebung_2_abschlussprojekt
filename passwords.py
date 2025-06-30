import streamlit as st
import streamlit_authenticator as stauth

names = ['Lukas']
usernames = ['lukas']
passwords = ['password123']

hashed_passwords = stauth.Hasher(passwords).generate()

authenticator = stauth.Authenticate(
    names,
    usernames,
    hashed_passwords,
    'cookie_name',
    'signature_key',
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('Login', location='main')
