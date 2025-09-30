from db import users_collection
from flask import request, flash, redirect, url_for, session, jsonify, render_template, current_app
from bson import ObjectId
from datetime import datetime
import os
from extensions.bcrypt import bcrypt
from utils.auth_checker import allowed_file, validate_password
from werkzeug.utils import secure_filename

def view_profile():
    user_id = session.get('user_id')
    if not user_id:
        flash("User not logged in", "danger")
        return redirect(url_for("auth_login"))

    if request.method == 'POST':
        action = request.form.get('action')

        if 'profile' in request.files:
            image = request.files['profile']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)

                users_collection.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'picture': filename}}
                )
                session['picture'] = filename
                flash("Profile picture updated!", "success")
        # ==== Update Info ====
        elif action == 'update_info':
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            email = request.form['email']

            update_data = {
                "firstname": firstname,
                "lastname": lastname,
                "email": email
            }

            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )

            session['name'] = f"{firstname} {lastname}"
            session['email'] = email
            session['fname'] = firstname
            session['lname'] = lastname

            flash("Profile updated successfully!", "success")

        # ==== Update Password ====
        elif action == 'update_password':
            current_pw = request.form['current_password']
            new_pw = request.form['new_password']
            confirm_pw = request.form['confirm_password']

            user = users_collection.find_one({'_id': ObjectId(user_id)})

            if not bcrypt.check_password_hash(user['password'], current_pw):
                flash("Current password is incorrect!", "danger")
            elif new_pw != confirm_pw:
                flash("New passwords do not match!", "danger")
            elif not validate_password(new_pw):
                flash("Password does not meet security requirements!", "warning")
            else:
                hashed_pw = bcrypt.generate_password_hash(new_pw).decode('utf-8')
                users_collection.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'password': hashed_pw}}
                )
                flash("Password updated successfully!", "success")

    user = users_collection.find_one({"_id": ObjectId(user_id)})
    return render_template('/profile/profile.html', 
                           user_firstname=user.get('firstname', ''),
                           user_lastname=user.get('lastname', ''),
                           user_email=user.get('email', ''),
                           user_bio=user.get('bio', ''))