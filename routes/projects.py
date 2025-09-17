from db import projects_collection as projects_collection
from db import column_collection as column_collection
from flask import request, flash, render_template, redirect, url_for, session

from bson import ObjectId
from datetime import datetime

def projects_list(template):
    try:
        user_id = session.get('user_id')
        user_projects = projects_collection.find({
            '$or': [
                {'user_id': user_id},
                {'members': user_id}
            ]
        }).sort('created_at', -1)
        
        projects = list(user_projects)

        total_projects = len(projects)
        active_projects = len([p for p in projects if p.get('status') == 'active'])
        completed_projects = len([p for p in projects if p.get('status') == 'completed'])
        on_hold_projects = len([p for p in projects if p.get('status') == 'on_hold'])
        
        stats = {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'on_hold_projects': on_hold_projects
        }
        
        return render_template(f'/main/{template}.html', projects=projects, stats = stats)
        
    except Exception as e:
        print(f"Projects list error: {e}")
        flash('An error occurred while loading projects.', 'error')
        return render_template('/main/projects.html', projects=[])

def project_create():
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        description = request.form['description'].strip()
        user_id = session.get('user_id')
        
        if not project_name:
            flash('Project name is required!', 'error')
            return render_template('/main/create_project.html')
        
        if not user_id:
            flash('You must be logged in to create a project.', 'error')
            return redirect(url_for('login'))
        
        try:
            existing_project = projects_collection.find_one({
                'project_name': project_name,
                'user_id': user_id
            })
            
            if existing_project:
                flash('A project with this name already exists!', 'error')
                return render_template('/main/create_project.html')
            
            project_data = {
                'project_name': project_name,
                'description': description,
                'user_id': user_id,
                'members': [user_id],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'status': 'active',
                'progress': 0
            }
            
            result = projects_collection.insert_one(project_data)
            
            if result.inserted_id:
                flash('Project created successfully!', 'success')
                return redirect(url_for('projects'))
            else:
                flash('Failed to create project. Please try again.', 'error')
                return render_template('/main/create_project.html')
                
        except Exception as e:
            print(f"Project creation error: {e}")
            flash('An error occurred while creating the project. Please try again.', 'error')
            return render_template('/main/create_project.html')
    
    return render_template('/main/create_project.html')

def project_view(project_id):
    try:
        user_id = session.get('user_id')
        
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            '$or': [
                {'user_id': user_id},
                {'members': user_id}
            ]
        })
        
        if not project:
            flash('Project not found or you do not have access to it.', 'error')
            return redirect(url_for('projects'))
        
        return render_template('/main/project_detail.html', project=project)
        
    except Exception as e:
        print(f"Project view error: {e}")
        flash('An error occurred while loading the project.', 'error')
        return redirect(url_for('projects'))

def project_add_member(project_id):
    try:
        user_id = session.get('user_id')
        project = projects_collection.find_one({
            '_id': project_id,
            'user_id': user_id
        })
        
        if not project:
            flash('Project not found or you do not have permission to manage it.', 'error')
            return redirect(url_for('projects'))
        
        if request.method == 'POST':
            member_email = request.form['member_email'].strip().lower()
            
            if not member_email:
                flash('Member email is required!', 'error')
                return render_template('/main/add_member.html', project=project)

            from db import users_collection
            member = users_collection.find_one({'email': member_email})
            
            if not member:
                flash('User with this email not found.', 'error')
                return render_template('/main/add_member.html', project=project)
            
            member_id = str(member['_id'])
            if member_id in project.get('members', []):
                flash('This user is already a member of the project.', 'info')
                return render_template('/main/add_member.html', project=project)

            result = projects_collection.update_one(
                {'_id': project_id},
                {
                    '$addToSet': {'members': member_id},
                    '$set': {'updated_at': datetime.now()}
                }
            )
            
            if result.modified_count > 0:
                flash(f'Successfully added {member["firstname"]} {member["lastname"]} to the project!', 'success')
                return redirect(url_for('project_view', project_id=project_id))
            else:
                flash('Failed to add member to project.', 'error')
                return render_template('/main/add_member.html', project=project)
        
        return render_template('/main/add_member.html', project=project)
        
    except Exception as e:
        print(f"Add member error: {e}")
        flash('An error occurred while adding the member.', 'error')
        return redirect(url_for('projects'))
    
def column_create(project_id):        
    try:
        if request.method == 'POST':
            label = request.form['label'].strip().lower()
                        
            column_data = {
                'label': label,
                'project': ObjectId(project_id),
            }

            result = column_collection.insert_one(column_data)
            if result.inserted_id:
                flash('Column created successfully!', 'success')
                return redirect(url_for('project_view', project_id = project_id))
        
        return render_template(url_for('view_project', project_id = project_id))
        
    except Exception as e:
        print(f"Add member error: {e}")
        flash('An error occurred while adding the member.', 'error')
        return redirect(url_for('projects'))