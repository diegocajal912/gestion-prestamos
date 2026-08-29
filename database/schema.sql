-- Script de creación de la Base de Datos y Estructura
CREATE DATABASE GestionPrestamos;
GO

USE GestionPrestamos;
GO

CREATE TABLE Clientes (
    ClienteID INT IDENTITY(1,1) PRIMARY KEY,
    Nombre VARCHAR(100) NOT NULL,
    Apellido VARCHAR(100) NOT NULL,
    Telefono VARCHAR(20) NULL
);

CREATE TABLE Prestamos (
    PrestamoID INT IDENTITY(1,1) PRIMARY KEY,
    ClienteID INT FOREIGN KEY REFERENCES Clientes(ClienteID),
    MontoPrestado DECIMAL(12,2) NOT NULL,
    TasaInteres DECIMAL(5,2) NOT NULL,
    MontoTotalDevolver DECIMAL(12,2) NOT NULL,
    FechaInicio DATE NOT NULL,
    FechaVencimiento DATE NOT NULL,
    Estado VARCHAR(20) DEFAULT 'Activo'
);
GO