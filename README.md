### **Real-Time Clinic Management System** 🏥  

A **Django Template Language (DTL) based real-time patient scheduling web app** for booking doctor sessions. It features a **waiting display screen**, allowing patients to check their turn remotely, reducing clinic crowding. Doctors can efficiently **manage patient records, diagnoses, and consultations**, ensuring a streamlined workflow. 🚀  


redis-server

daphne -b 0.0.0.0 -p 8000 clinic_management.asgi:application

psql postgres
# Inside psql shell:
CREATE DATABASE pmc_db;
CREATE USER postgres WITH PASSWORD 'postgres';
ALTER ROLE postgres SET client_encoding TO 'utf8';
ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
ALTER ROLE postgres SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE djangodb TO user;
\q