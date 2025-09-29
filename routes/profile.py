from db import projects_collection, column_collection, tasks_collection, users_collection
from flask import request, flash, redirect, url_for, session, jsonify, render_template
from bson import ObjectId
from datetime import datetime

def view_profile():
    return render_template('/profile/profile.html')