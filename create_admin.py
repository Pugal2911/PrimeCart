import mysql.connector
from werkzeug.security import generate_password_hash

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "primecart",
    "use_pure": True
}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
ADMIN_FULL_NAME = "System Administrator"
ADMIN_EMAIL = "admin@gmail.com"

hashed_password = generate_password_hash(
    ADMIN_PASSWORD,
    method="pbkdf2:sha256",
    salt_length=16
)

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    sql = """
    INSERT INTO users (username, password_hash, role, full_name, email)
    VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(sql, (
        ADMIN_USERNAME,
        hashed_password,
        "admin",
        ADMIN_FULL_NAME,
        ADMIN_EMAIL
    ))

    conn.commit()
    print("Admin user created successfully")

except mysql.connector.Error as err:
    print("Database error:", err)

finally:
    cursor.close()
    conn.close()
