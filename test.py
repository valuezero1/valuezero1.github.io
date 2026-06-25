from database import cursor, conn

cursor.execute("INSERT INTO tobacco(name, grams) VALUES (?, ?)", ("Al Fakher", 1000))
cursor.execute("INSERT INTO tobacco(name, grams) VALUES (?, ?)", ("Darkside", 800))
conn.commit()