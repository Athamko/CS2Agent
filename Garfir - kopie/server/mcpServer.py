from mcp.server.fastmcp import FastMCP
import smtplib
from email.mime.text import MIMEText
import psycopg2
import random

# Create an MCP server
mcp = FastMCP("GarfirServer", json_response=True)


# Add an addition tool
@mcp.tool()
def get_a_tactic(map_name: str) -> str:
    """Slouží k získání náhodné herní taktiky nebo strategie pro hru Counter-Strike. Zavolej tento nástroj vždy, když se uživatel ptá, jak hrát dané kolo, jakou zvolit strategii, nebo chce tip pro konkrétní mapu (např. Mirage, Inferno, Dust2). Vyžaduje zadání názvu mapy."""

    try:
        # Zde bys měl ideálně načítat hesla z proměnných prostředí (os.getenv), ne natvrdo
        conn = psycopg2.connect(
            dbname="cs2tactics", user="postgres", host="localhost", password="garfir123"
        )
        cur = conn.cursor()

        # SQL dotaz: Vybere text, kde sedí mapa, seřadí náhodně a vezme 1
        query = "SELECT strategy FROM Strategies WHERE map LIKE %s ORDER BY RANDOM() LIMIT 1"
        cur.execute(query, (map_name,))

        result = cur.fetchone()
        conn.close()

        if result:
            return result[0]  # Vracíme text taktiky
        else:
            return f"Pro mapu {map_name} nemám v databázi žádnou taktiku, sorry."

    except Exception as e:
        return f"Chyba databáze: {e}"


@mcp.tool()
def message_richard() -> str:
    """Popisek"""  # to je EXEKUce / dluhy /...
    sender = "mail"
    receiver = "mail"
    password = "pswrd"

    # Předem stanovený obsah s placeholders
    contract_id = random.randint(1000, 9999)
    money_amount = str(random.randint(2, 6)) + " " + str(random.randint(100, 860))

    subject = f"Cau"

    body = f"""
    ahoj
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    try:
        # Připojení k Gmail serveru (pro jiné maily hledej 'smtp server settings')
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        return "E-mail byl úspěšně odeslán."
    except Exception as e:
        return f"Nepovedlo se odeslat mail: {e}"


# Run with default stdio transport
if __name__ == "__main__":
    mcp.run()
