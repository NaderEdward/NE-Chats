from flask import redirect, session
from functools import wraps
import mysql.connector
import csv
import os

conn = mysql.connector.connect(
  host="...",
  user="...",
  password="...",
  database="...."
)

db = conn.cursor()
##################

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def add_user(name, password, phone_number, country):
    db.execute("SELECT * FROM users")
    users = db.fetchall()
    try:
        len_users = users[-1][1]
    except IndexError:
        db.execute("INSERT INTO users (name, password, phone_number, country) VALUES (%s, %s, %s, %s)", [name, password, phone_number, country])
        conn.commit()
        db.execute("SELECT * FROM users")
        users = db.fetchall()
        return users[-1][0]
    ###
    for user in users:
        if (user[3] == phone_number) and (user[4] == country):
            return "Phone number already used!!!"
        else:
            db.execute("INSERT INTO users (name, password, phone_number, country) VALUES (%s, %s, %s, %s)", [name, password, phone_number, country])
            conn.commit()
            db.execute("SELECT * FROM users")
            users = db.fetchall()
            return users[-1][0]
    return 0

def get_last_5_notifications(user_id):
    db.execute("SELECT * FROM notifications WHERE (id) = (%s)", [user_id])
    _ = db.fetchall()
    notifications = []
    for notif in reversed(_):
        notifications.append(notif)
    return notifications[:5]

def get_user_info_by_phone_number_and_country(phone_number, country):
    db.execute("SELECT * FROM users WHERE (phone_number, country) = (%s, %s)", [phone_number, country])
    user = db.fetchall()
    return user[0]


def get_user_info_by_user_id(user_id):
    db.execute("SELECT * FROM users WHERE user_id = %s", [user_id])
    user = db.fetchall()
    return user[0]


def create_user_contact_list(user_id):
    with open(f"/home/NaderEdward/mysite/files/{user_id}_contacts_list.csv", "w") as contact_list:
        writer = csv.DictWriter(contact_list, fieldnames=["name", "user_id"])
        writer.writeheader()
    return user_id

def add_contact_(user_id_1, name, user_id_2):
    with open(f"/home/NaderEdward/mysite/files/{user_id_1}_contacts_list.csv", "a") as contact_list:
        appender = csv.DictWriter(contact_list, fieldnames=["name", "user_id"])
        appender.writerow({"name": name, "user_id": user_id_2})
    contact_info = get_user_info_by_user_id(user_id_1)
    db.execute("INSERT INTO notifications (id, notification) VALUES (%s, %s)", [user_id_2, f"{contact_info[1]} added you as a contact! (Country: {contact_info[4]} | Phone number: {contact_info[3]})"])
    conn.commit()
    return (user_id_1, user_id_2)

def remove_contact_(user_id_1, user_id_2):
    file_name = (f"/home/NaderEdward/mysite/files/{user_id_1}_contacts_list.csv")
    ###
    with open(file_name, "r") as contact_list:
            reader = csv.DictReader(contact_list)
            contacts = [contact for contact in reader if contact["user_id"] != user_id_2]
    with open(file_name, "w") as contact_list:
        writer = csv.DictWriter(contact_list, fieldnames=["name", "user_id"])
        writer.writeheader()
        for contact_ in contacts:
            writer.writerow(contact_)
    contact_info = get_user_info_by_user_id(user_id_1)
    db.execute("INSERT INTO notifications (id, notification) VALUES (%s, %s)", [user_id_2, f"{contact_info[1]} removed you as a contact! (Country: {contact_info[4]} | Phone number: {contact_info[3]})"])
    return True


def get_contacts(user_id):
    with open(f"/home/NaderEdward/mysite/files/{user_id}_contacts_list.csv", "r") as contact_list:
        reader = csv.DictReader(contact_list)
        contacts = []
        for contact in reader:
            name, user_id = contact["name"], contact["user_id"]
            contacts.append((name, user_id))
    return contacts

def create_messages_file(id_1, id_2):
    with open(f"/home/NaderEdward/mysite/files/{id_1}_{id_2}_messages_file.csv", "w") as messages_file:
        writer = csv.DictWriter(messages_file, fieldnames=["message", "from_id", "to_id"])
        writer.writeheader()
    return "{id_1}_{id_2}_contacts_list.csv"

def delete_messages_file(id_1, id_2):
    file_name = ""
    # Search for file in directory
    # if file is found using combination of ids then record file name to be deleted
    if os.path.exists(f"/home/NaderEdward/mysite/files/{id_1}_{id_2}_messages_file.csv"):
        file_name = (f"/home/NaderEdward/mysite/files/{id_1}_{id_2}_messages_file.csv")
    elif os.path.exists(f"/home/NaderEdward/mysite/files/{id_2}_{id_1}_messages_file.csv"):
        file_name = (f"/home/NaderEdward/mysite/files/{id_2}_{id_1}_messages_file.csv")
    else:
        return None
    # delete file
    os.remove(file_name)
    return file_name

def get_messages(this_users_id, other_users_id):
    file_name = ""
    # Search for file in directory
    # if file is found using combination of ids then record file name to be read
    if os.path.exists(f"/home/NaderEdward/mysite/files/{this_users_id}_{other_users_id}_messages_file.csv"):
        file_name = (f"/home/NaderEdward/mysite/files/{this_users_id}_{other_users_id}_messages_file.csv")
    elif os.path.exists(f"/home/NaderEdward/mysite/files/{other_users_id}_{this_users_id}_messages_file.csv"):
        file_name = (f"/home/NaderEdward/mysite/files/{other_users_id}_{this_users_id}_messages_file.csv")
    else:
        return None
    # get all messages from file
    with open(file_name, "r") as messages_file:
        reader = csv.DictReader(messages_file)
        # Seperate chats by recipient and sender
        messages = []
        order = [0]
        for row in reader:
            messages.append(row["message"])
            if int(row["from_id"]) == int(this_users_id):
                order.append(1)
            else:
                order.append(0)
    return messages, order

def add_message(user_id, other_id, message):
    file_name = ""
    # Search for file in directory
    # if file is found using combination of ids then record file name to be read
    if os.path.exists(f"/home/NaderEdward/mysite/files/{user_id}_{other_id}_messages_file.csv"):
        file_name = (f"/home/NaderEdward/mysite/files/{user_id}_{other_id}_messages_file.csv")
    elif os.path.exists(f"/home/NaderEdward/mysite/files/{other_id}_{user_id}_messages_file.csv"):
        file_name = (f"/home/NaderEdward/mysite/files/{other_id}_{user_id}_messages_file.csv")
    else:
        return None
    with open(file_name, "a") as messages_file:
        appender = csv.DictWriter(messages_file, fieldnames=["message", "from_id", "to_id"])
        appender.writerow({"message": message, "from_id": user_id, "to_id": other_id})
    contact_info = get_user_info_by_user_id(user_id)
    db.execute("INSERT INTO notifications (id, notification) VALUES (%s, %s)", [other_id, f"{contact_info[1]} sent you a message!)"])
    return message






