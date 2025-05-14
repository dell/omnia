CREATE DATABASE IF NOT EXISTS idrac_telemetrydb;

CREATE TABLE IF NOT EXISTS idrac_telemetrydb.services (
    ip VARCHAR(255) PRIMARY KEY,
    serviceType INT,
    authType INT,
    auth VARCHAR(4096)
);
