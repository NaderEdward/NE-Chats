from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from datetime import date
from functions import *
import mysql.connector
from cs50 import SQL
import csv

# Configure application
app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

conn = mysql.connector.connect(
  host="...",
  user="...",
  password="...",
  database="..."
)

db = conn.cursor()

countries = ["EGYPT", "DUBAI", "USA"] # countries that can be chosen | more can be added here


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

#################################################################################

@app.route("/")
@login_required
def home():
    user_id = session["user_id"]
    contacts = get_contacts(user_id)
    notifications = get_last_5_notifications(user_id)
    return render_template("home.html", contacts_layout=contacts, notifications=notifications)

@app.route("/open_chat", methods=["GET", "POST"])
@login_required
def open_chat():
    user_id = session["user_id"]
    contacts = get_contacts(user_id)
    # Get user_id of other chat's side
    contact_name = request.form["contact_name"]
    name, _ = contact_name.split("ID(")
    contact_user_id =_.rstrip(")")
    # Find all mesages between this user and the other
    messages, order = get_messages(user_id, contact_user_id)
    # render template of both chats for sender and recipent ordered
    return render_template("open_chat.html", contacts_layout=contacts, contact_name=name, messages=messages, order=order, other_id=contact_user_id)

@app.route("/send_message", methods=["GET", "POST"])
@login_required
def send_message():
    # get user_id that sent and user_id that recives
    user_id = session["user_id"]
    other_id = int(request.form.get("other_id"))
    message = request.form.get("message")
    ###
    name = get_user_info_by_user_id(other_id)[1]
    contacts = get_contacts(user_id)
    # enter message into csv file with id from and id to
    add_message(user_id, other_id, message)
    # Find all mesages between this user and the other including new message
    messages, order = get_messages(user_id, other_id)
    # render template of both chats for sender and recipent ordered
    return render_template("open_chat.html", contacts_layout=contacts, contact_name=name, messages=messages, order=order, other_id=other_id)

@app.route("/reload_chat", methods=["GET", "POST"])
@login_required
def reload_chat():
    user_id = session["user_id"]
    contacts = get_contacts(user_id)
    other_id = int(request.form.get("other_id"))
    name = get_user_info_by_user_id(other_id)[1]
    # Find all mesages between this user and the other
    messages, order = get_messages(user_id, other_id)
    # render template of both chats for sender and recipent ordered
    return render_template("open_chat.html", contacts_layout=contacts, contact_name=name, messages=messages, order=order, other_id=other_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget user
    session.clear()

    if request.method == "POST":
        phone_number = request.form.get("login_phone_number")
        password = request.form.get("login_password")
        country = request.form.get("login_country")
        # Make sure phone number is submitted
        if not phone_number or len(phone_number) != 11:
            return render_template("apology.html", msg="Please enter a valid phone number")

        # Make sure password submitted
        elif not password:
            return render_template("apology.html", msg="Please enter password")

        # Make sure country selected
        elif not country:
            return render_template("apology.html", msg="Please select country")

        # Look for phone number
        db.execute("SELECT * FROM users WHERE (phone_number, country) = (%s, %s)", [phone_number, country])
        rows = db.fetchall()
        # Ensure phone number exists and password is correct
        if len(rows)!= 1 or rows[0][2] != password or rows[0][4] != country:
            return render_template("apology.html",  msg ="Invalid phone number and/or password for selected country")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Go to home page
        return redirect("/")

    else:
        return render_template("login.html", countries=countries)

###
@app.route("/logout")
def logout():
    # Forget user
    session.clear()

    # Go to login form
    return redirect("/login")

###
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("register_name")
        phone_number = request.form.get("register_phone_number")
        password = request.form.get("register_password")
        confirmation = request.form.get("confirm_register_password")
        country = request.form.get("register_country")
        # Make sure phone number is submitted
        if not phone_number or len(phone_number) != 11:
            return render_template("apology.html", msg="Please enter a valid phone number")

        # Make sure password submitted
        elif not password:
            return render_template("apology.html", msg="Please enter password")

        # Make sure there are no accounts with the same phone_number
        db.execute("SELECT * FROM users WHERE phone_number = %s", [phone_number])
        rows = db.fetchall()

        if rows == None:
            # Check that both passwords are the same
            if password != confirmation:
                return render_template("apology.html", msg ="Passwords do not match")
            # Enter data into database
            new_user = add_user(name, password, phone_number, country)
            # Log user in
            session["user_id"] = new_user
            return redirect("/")

        # Make sure phone number does not exist
        if len(rows) == 1 and rows[0][4] == country:
            return render_template("apology.html", msg = "An account is using this phone number in the selected country")
        # Check that both passwords are the same
        if password != confirmation:
            return render_template("apology.html", msg ="Passwords do not match")
         # Enter data into database
        new_user = add_user(name, password, phone_number, country)
        print(new_user)
        create_user_contact_list(new_user)
        # Log user in
        session["user_id"] = new_user

        return redirect("/")
    else:
        # Go to main page
        return render_template("register.html", countries=countries)



@app.route("/contacts")
@login_required
def contacts():
    user_id = session["user_id"]
    contacts_list = get_contacts(user_id)
    contact_names = []
    contacts = []
    for contact in contacts_list:
        contact_names.append(contact[0])
        contacts.append(get_user_info_by_user_id(contact[1]))
    return render_template("contacts.html", contacts_layout=contacts_list, contacts=contacts, countries=countries)


@app.route("/add_contact", methods=["GET", "POST"])
@login_required
def add_contact():
    phone_number = request.form.get("add_c_phone_number")
    country = request.form.get("add_c_country")
    password = request.form.get("add_c_password")
    ###
    # Make sure valid phone_number was submitted
    if not phone_number or len(phone_number) != 11:
        return render_template("apology.html", msg="Please enter a valid phone number")
    # Make sure password submitted
    elif not password:
        return render_template("apology.html", msg="Please enter password")
    elif not country:
        return render_template("apology.html", msg="Please select country")
    ###
    user_id = session["user_id"]
    this_user = get_user_info_by_user_id(user_id)
    # make sure password is correct
    if this_user[2] != password:
        return render_template("apology.html", msg ="Password incorrect")
    # make sure new contact isn't already added
    contacts = get_contacts(user_id)
    for contact in contacts:
        if get_user_info_by_user_id(contact[1])[3] == phone_number:
            return render_template("apology.html", msg ="Number already in contacts!")
    ###
    new_contact = get_user_info_by_phone_number_and_country(phone_number, country)
    # make sure they're not adding themselves
    if new_contact[0] == this_user[0]:
        return render_template("apology.html", msg ="Can't add yourself!")
    # Create new csv file between this user and other user
    create_messages_file(user_id, new_contact[0])
    # add user to list of contacts for both users
    add_contact_(user_id, new_contact[1], new_contact[0])
    add_contact_(new_contact[0], this_user[1] , user_id)
    ###
    return redirect("/contacts")


@app.route("/remove_contact", methods=["GET", "POST"])
@login_required
def remove_contact():
    phone_number = request.form.get("remove_c_phone_number")
    country = request.form.get("remove_c_country")
    password = request.form.get("remove_c_password")
    ###
    # Make sure valid phone_number was submitted
    if not phone_number or len(phone_number) != 11:
        return render_template("apology.html", msg="Please enter a valid phone number")
    # Make sure password submitted
    elif not password:
        return render_template("apology.html", msg="Please enter password")
    elif not country:
        return render_template("apology.html", msg="Please select country")
    ###
    user_id = session["user_id"]
    this_user = get_user_info_by_user_id(user_id)
    # make sure password is correct
    if this_user[2] != password:
        return render_template("apology.html", msg ="Password incorrect")
    # make sure new contact isn't already added
    contacts = get_contacts(user_id)
    for contact in contacts:
        if int(contact[1]) == int(get_user_info_by_phone_number_and_country(phone_number, country)[0]):
            # delete csv file between this user and other user
            delete_messages_file(user_id, contact[1])
            # add user to list of contacts for both users
            remove_contact_(user_id, contact[1])
            remove_contact_(contact[1], user_id)
            ###
            return redirect("/contacts")
            ###
    return render_template("apology.html", msg ="Couldn't remove contact")








