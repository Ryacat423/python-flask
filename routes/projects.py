from db import projects_collection as projects_collection
from db import column_collection as column_collection
from db import tasks_collection as tasks_collection
from db import users_collection as users_collection

from utils.socket import broadcast_to_project, get_socketio

from flask import request, flash, render_template, redirect, url_for, session, jsonify

from bson import ObjectId
from datetime import datetime

def projects_list(template):
    try:
        user_id = session.get('user_id')
        user_projects = projects_collection.find({
            '$or': [
                {'user_id': user_id},
                {'members': ObjectId(user_id)}
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
                'members': [ObjectId(user_id)],
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
                {'members': ObjectId(user_id)}
            ]
        })
        
        if not project:
            flash('Project not found or you do not have access to it.', 'error')
            return redirect(url_for('projects'))

        columns_pipeline = [
            {'$match': {'project': ObjectId(project_id)}},
            {'$lookup': {
                'from': 'tasks',
                'localField': '_id',
                'foreignField': 'column_id',
                'as': 'tasks'
            }},
            {'$addFields': {
                'task_count': {'$size': '$tasks'}
            }},
            {'$sort': {'order': 1}}
        ]
        
        columns = list(column_collection.aggregate(columns_pipeline))
        
        total_tasks = sum(col.get('task_count', 0) for col in columns)
        task_stats = {}
        if columns:
            task_pipeline = [
                {'$match': {'project_id': ObjectId(project_id)}},
                {'$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }}
            ]
            task_stats_result = list(tasks_collection.aggregate(task_pipeline))
            for stat in task_stats_result:
                task_stats[stat['_id']] = stat['count']
        
        stats = {
            'total_projects': total_tasks,
            'active_projects': task_stats.get('in_progress', 0),
            'completed_projects': task_stats.get('completed', 0),
            'on_hold_projects': len(project.get('members', [])),
        }
        
        return render_template('/main/project_detail.html', 
                             project=project, 
                             columns=columns,
                             stats=stats)
        
    except Exception as e:
        print(f"Project view error: {e}")
        flash('An error occurred while loading the project.', 'error')
        return redirect(url_for('projects'))
    
def column_create(project_id):        
    try:
        if request.method == 'POST':
            label = request.form['label'].strip()
            color = request.form.get('color', 'light-blue').strip()
            user_id = session.get('user_id')

            project = projects_collection.find_one({
                '_id': ObjectId(project_id),
                '$or': [
                    {'user_id': user_id},
                    {'members': ObjectId(user_id)}
                ]
            })
            
            if not project:
                flash('Project not found or you do not have access to it.', 'error')
                return redirect(url_for('projects'))

            existing_column = column_collection.find_one({
                'project': ObjectId(project_id),
                'label': {'$regex': f'^{label}$', '$options': 'i'}
            })
            
            if existing_column:
                flash('A column with this name already exists in this project.', 'error')
                return redirect(url_for('view_project', project_id=project_id))
            
            last_column = column_collection.find_one(
                {'project': ObjectId(project_id)},
                sort=[('order', -1)]
            )
            next_order = (last_column.get('order', -1) + 1) if last_column else 0
                        
            column_data = {
                'label': label,
                'color': color,
                'project': ObjectId(project_id),
                'created_at': datetime.now(),
                'created_by': user_id,
                'order': next_order
            }

            result = column_collection.insert_one(column_data)
            if result.inserted_id:
                socketio = get_socketio()
                if socketio:
                    column_data_broadcast = {
                        '_id': str(result.inserted_id),
                        'label': label,
                        'color': color,
                        'order': next_order,
                        'task_count': 0
                    }
                    
                    broadcast_to_project(
                        project_id,
                        'column_created',
                        {
                            'type': 'column_create',
                            'column': column_data_broadcast,
                            'userId': user_id,
                            'userName': session.get('name', 'Anonymous User'),
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                
                flash('Column created successfully!', 'success')
                return redirect(url_for('view_project', project_id=project_id))
            else:
                flash('Failed to create column. Please try again.', 'error')
                return redirect(url_for('view_project', project_id=project_id))
        
        return redirect(url_for('view_project', project_id=project_id))
        
    except Exception as e:
        print(f"Column creation error: {e}")
        flash('An error occurred while creating the column.', 'error')
        return redirect(url_for('view_project', project_id=project_id))

def task_create(project_id):
    try:
        if request.method == 'POST':
            title = request.form['title'].strip()
            description = request.form.get('description', '').strip()
            task_type = request.form.get('type', 'task').strip()
            priority = request.form.get('priority', 'medium').strip()
            due_date_str = request.form.get('due_date', '').strip()
            column_id = request.form['column_id'].strip()
            labels_str = request.form.get('labels', '').strip()
            user_id = session.get('user_id')

            if not title:
                flash('Task title is required!', 'error')
                return redirect(url_for('view_project', project_id=project_id))
                
            if not column_id:
                flash('Column selection is required!', 'error')
                return redirect(url_for('view_project', project_id=project_id))

            project = projects_collection.find_one({
                '_id': ObjectId(project_id),
                '$or': [
                    {'user_id': user_id},
                    {'members': ObjectId(user_id)}
                ]
            })
            
            if not project:
                flash('Project not found or you do not have access to it.', 'error')
                return redirect(url_for('projects'))

            column = column_collection.find_one({
                '_id': ObjectId(column_id),
                'project': ObjectId(project_id)
            })
            
            if not column:
                flash('Invalid column selected.', 'error')
                return redirect(url_for('view_project', project_id=project_id))

            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid due date format.', 'error')
                    return redirect(url_for('view_project', project_id=project_id))

            labels = []
            if labels_str:
                labels = [label.strip() for label in labels_str.split(',') if label.strip()]

            user_info = users_collection.find_one({'_id': ObjectId(user_id)})
            assignee_name = f"{user_info.get('firstname', '')} {user_info.get('lastname', '')}".strip()
            assignee_initials = ''.join([name[0].upper() for name in assignee_name.split() if name])[:2]

            last_task = tasks_collection.find_one(
                {'column_id': ObjectId(column_id)},
                sort=[('order', -1)]
            )
            next_order = (last_task.get('order', -1) + 1) if last_task else 0
            
            task_data = {
                'title': title,
                'description': description,
                'type': task_type,
                'priority': priority,
                'due_date': due_date,
                'labels': labels,
                'column_id': ObjectId(column_id),
                'project_id': ObjectId(project_id),
                'created_by': user_id,
                'assigned_to': user_id,
                'assignee_name': assignee_name,
                'assignee_initials': assignee_initials,
                'status': 'todo',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'order': next_order
            }
            
            result = tasks_collection.insert_one(task_data)
            
            if result.inserted_id:
                socketio = get_socketio()
                if socketio:
                    task_data_broadcast = {
                        '_id': str(result.inserted_id),
                        'title': title,
                        'description': description,
                        'type': task_type,
                        'priority': priority,
                        'due_date': due_date.isoformat() if due_date else None,
                        'labels': labels,
                        'assignee_name': assignee_name,
                        'assignee_initials': assignee_initials
                    }
                    
                    broadcast_to_project(
                        project_id,
                        'task_created',
                        {
                            'type': 'task_create',
                            'task': task_data_broadcast,
                            'columnId': column_id,
                            'userId': user_id,
                            'userName': session.get('name', 'Anonymous User'),
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                
                flash('Task created successfully!', 'success')
                return redirect(url_for('view_project', project_id=project_id))
            else:
                flash('Failed to create task. Please try again.', 'error')
                return redirect(url_for('view_project', project_id=project_id))
        
        return redirect(url_for('view_project', project_id=project_id))
        
    except Exception as e:
        print(f"Task creation error: {e}")
        flash('An error occurred while creating the task.', 'error')
        return redirect(url_for('view_project', project_id=project_id))

def task_move(project_id):
    try:
        data = request.get_json()
        task_id = data.get('taskId')
        source_column_id = data.get('sourceColumnId')
        target_column_id = data.get('targetColumnId')
        user_id = session.get('user_id')

        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            '$or': [
                {'user_id': user_id},
                {'members': ObjectId(user_id)}
            ]
        })
        
        if not project:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        task = tasks_collection.find_one({
            '_id': ObjectId(task_id),
            'project_id': ObjectId(project_id)
        })
        
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'}), 404

        source_column = column_collection.find_one({
            '_id': ObjectId(source_column_id),
            'project': ObjectId(project_id)
        })
        
        target_column = column_collection.find_one({
            '_id': ObjectId(target_column_id),
            'project': ObjectId(project_id)
        })
        
        if not source_column or not target_column:
            return jsonify({'success': False, 'message': 'Invalid columns'}), 400

        last_task = tasks_collection.find_one(
            {'column_id': ObjectId(target_column_id)},
            sort=[('order', -1)]
        )
        next_order = (last_task.get('order', -1) + 1) if last_task else 0
        update_result = tasks_collection.update_one(
            {'_id': ObjectId(task_id)},
            {
                '$set': {
                    'column_id': ObjectId(target_column_id),
                    'updated_at': datetime.now(),
                    'order': next_order
                }
            }
        )
        
        if update_result.modified_count > 0:
            return jsonify({
                'success': True,
                'message': 'Task moved successfully',
                'task_id': task_id,
                'source_column_id': source_column_id,
                'target_column_id': target_column_id
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update task'}), 500
            
    except Exception as e:
        print(f"Task move error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

def project_add_member(project_id):
    try:
        user_id = session.get('user_id')
        
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
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

            member = users_collection.find_one({'email': member_email})
            
            if not member:
                flash('User with this email not found.', 'error')
                return render_template('/main/add_member.html', project=project)
            
            member_object_id = member['_id']
            if member_object_id in project.get('members', []):
                flash('This user is already a member of the project.', 'info')
                return render_template('/main/add_member.html', project=project)

            result = projects_collection.update_one(
                {'_id': ObjectId(project_id)},
                {
                    '$addToSet': {'members': member_object_id},
                    '$set': {'updated_at': datetime.now()}
                }
            )
            
            if result.modified_count > 0:
                flash(f'Successfully added {member["firstname"]} {member["lastname"]} to the project!', 'success')
                return redirect(url_for('project_view_members', project_id=project_id))
            else:
                flash('Failed to add member to project.', 'error')
                return render_template('/main/add_member.html', project=project)
        
        return render_template('/main/add_member.html', project=project)
        
    except Exception as e:
        print(f"Add member error: {e}")
        flash('An error occurred while adding the member.', 'error')
        return redirect(url_for('projects'))

def project_view_members(project_id):
    try:
        user_id = session.get('user_id')
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            '$or': [
                {'user_id': user_id},
                {'members': ObjectId(user_id)}
            ]
        })

        if not project:
            flash('Project not found or you do not have access to it.', 'error')
            return redirect(url_for('projects'))

        members_pipeline = [
            {'$match': {'_id': ObjectId(project_id)}},
            {'$lookup': {
                'from': 'users',
                'localField': 'members',
                'foreignField': '_id',
                'as': 'member_details'
            }},
            {'$project': {
                'project_name': 1,
                'description': 1,
                'user_id': 1,
                'member_details': {
                    '_id': 1,
                    'firstname': 1,
                    'lastname': 1,
                    'email': 1,
                    'picture': 1
                }
            }}
        ]
        
        result = list(projects_collection.aggregate(members_pipeline))
        
        if not result:
            flash('Project not found.', 'error')
            return redirect(url_for('projects'))
            
        project_with_members = result[0]
        members = project_with_members.get('member_details', [])
        
        for member in members:
            member['is_owner'] = str(member['_id']) == project['user_id']
        
        return render_template('/main/view_members.html', 
                             project=project_with_members, 
                             members=members,
                             is_owner=(user_id == project['user_id']))
        
    except Exception as e:
        print(f"View members error: {e}")
        flash('An error occurred while loading project members.', 'error')
        return redirect(url_for('projects'))
    
def project_remove_member(project_id):
    try:
        user_id = session.get('user_id')
        member_id = request.form.get('member_id')
        
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            'user_id': user_id
        })

        if not project:
            flash('Project not found or you do not have permission to manage it.', 'error')
            return redirect(url_for('projects'))
        
        if not member_id:
            flash('Invalid member selected.', 'error')
            return redirect(url_for('view_members', project_id=project_id))
        
        if member_id == user_id:
            flash('You cannot remove yourself from the project.', 'error')
            return redirect(url_for('view_members', project_id=project_id))

        result = projects_collection.update_one(
            {'_id': ObjectId(project_id)},
            {
                '$pull': {'members': ObjectId(member_id)},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        if result.modified_count > 0:
            member = users_collection.find_one({'_id': ObjectId(member_id)})
            if member:
                flash(f'Successfully removed {member["firstname"]} {member["lastname"]} from the project.', 'success')
            else:
                flash('Member removed successfully.', 'success')
        else:
            flash('Failed to remove member from project.', 'error')
            
    except Exception as e:
        print(f"Remove member error: {e}")
        flash('An error occurred while removing the member.', 'error')
    
    return redirect(url_for('view_members', project_id=project_id))