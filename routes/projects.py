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
        pipeline = [
            {
                '$match': {
                    '$or': [
                        {'user_id': user_id},
                        {'members': ObjectId(user_id)}
                    ]
                }
            },
            {
                '$lookup': {
                    'from': 'tasks',
                    'localField': '_id',
                    'foreignField': 'project_id',
                    'as': 'tasks'
                }
            },
            {
                '$lookup': {
                    'from': 'columns',
                    'localField': '_id',
                    'foreignField': 'project',
                    'as': 'columns'
                }
            },
            {
                '$addFields': {
                    'total_tasks': {'$size': '$tasks'},
                    'done_column': {
                        '$arrayElemAt': [
                            {
                                '$filter': {
                                    'input': '$columns',
                                    'as': 'col',
                                    'cond': {'$eq': ['$$col.label', 'Done']}
                                }
                            },
                            0
                        ]
                    }
                }
            },
            {
                '$addFields': {
                    'completed_tasks': {
                        '$size': {
                            '$filter': {
                                'input': '$tasks',
                                'as': 'task',
                                'cond': {
                                    '$eq': ['$$task.column_id', '$done_column._id']
                                }
                            }
                        }
                    }
                }
            },
            {
                '$addFields': {
                    'progress': {
                        '$cond': {
                            'if': {'$gt': ['$total_tasks', 0]},
                            'then': {
                                '$round': [
                                    {'$multiply': [
                                        {'$divide': ['$completed_tasks', '$total_tasks']},
                                        100
                                    ]},
                                    0
                                ]
                            },
                            'else': 0
                        }
                    },
                    'member_count': {
                        '$add': [
                            {'$size': {'$ifNull': ['$members', []]}}
                        ]
                    },
                    'status': {
                        '$switch': {
                            'branches': [
                                {
                                    'case': {'$eq': ['$total_tasks', 0]},
                                    'then': 'not-started'
                                },
                                {
                                    'case': {'$eq': ['$completed_tasks', '$total_tasks']},
                                    'then': 'completed'
                                },
                                {
                                    'case': {'$gt': ['$completed_tasks', 0]},
                                    'then': 'in-progress'
                                }
                            ],
                            'default': 'not-started'
                        }
                    }
                }
            },
            {'$sort': {'created_at': -1}}
        ]
        
        projects = list(projects_collection.aggregate(pipeline))
        for project in projects:
            if 'created_at' in project:
                project['formatted_date'] = project['created_at'].strftime('%b %d, %Y')
            else:
                project['formatted_date'] = 'N/A'
            
            color_map = {
                'blue': 'color-blue',
                'green': 'color-green',
                'pink': 'color-pink',
                'orange': 'color-orange',
                'purple': 'color-purple',
                'gray': 'color-gray'

            }
            project['color_class'] = color_map.get(project.get('color', 'blue'), 'color-blue')
        
        return render_template(f'/main/{template}.html', projects=projects)
        
    except Exception as e:
        print(f"Projects list error: {e}")
        flash('An error occurred while loading projects.', 'error')
        return render_template('/main/projects.html', projects=[])

def project_create():
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        description = request.form['description'].strip()
        project_color = request.form.get('project_color', 'blue').strip()
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
                'color': project_color,
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

        projects_collection.update_one(
            {'_id': ObjectId(project_id)},
            {
                '$set': {
                    f'last_viewed.{user_id}': datetime.now()
                }
            }
        )

        # Fixed aggregation pipeline
        columns_pipeline = [
            {'$match': {'project': ObjectId(project_id)}},
            {'$lookup': {
                'from': 'tasks',
                'let': {'column_id': '$_id'},
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                    {'$eq': ['$column_id', '$$column_id']},
                                    {'$eq': ['$project_id', ObjectId(project_id)]}
                                ]
                            }
                        }
                    },
                    {'$lookup': {
                        'from': 'comments',
                        'localField': '_id',
                        'foreignField': 'task_id',
                        'as': 'comments'
                    }},
                    {'$addFields': {
                        'comment_count': {'$size': '$comments'}
                    }},
                    {'$project': {
                        'comments': 0  # Remove comments array, keep only count
                    }}
                ],
                'as': 'tasks'
            }},
            {'$addFields': {
                'task_count': {'$size': '$tasks'}
            }},
            {'$sort': {'order': 1}}
        ]
        
        columns = list(column_collection.aggregate(columns_pipeline))
        
        return render_template('/main/project_detail.html', 
                             project=project, 
                             columns=columns)
        
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
    
def project_view_members(project_id):
    try:
        user_id = session.get('user_id')

        if not project_id or not ObjectId.is_valid(project_id):
            flash('Invalid project ID.', 'error')
            return redirect(url_for('projects'))
        
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
        
        if not project_id or not ObjectId.is_valid(project_id):
            print(f"Invalid project ID format: {project_id}")
            flash('Invalid project ID.', 'error')
            return redirect(url_for('projects'))
        
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            'user_id': user_id
        })

        if not project:
            flash('Project not found or you do not have permission to manage it.', 'error')
            return redirect(url_for('projects'))
        
        if not member_id:
            flash('Invalid member selected.', 'error')
            return redirect(url_for('project_view_members', project_id=project_id))
        
        if member_id == user_id:
            flash('You cannot remove yourself from the project.', 'error')
            return redirect(url_for('project_view_members', project_id=project_id))

        if not ObjectId.is_valid(member_id):
            print(f"Invalid member ID format: {member_id}")
            flash('Invalid member ID.', 'error')
            return redirect(url_for('project_view_members', project_id=project_id))

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

                socketio = get_socketio()
                if socketio:
                    broadcast_to_project(
                        project_id,
                        'member_removed',
                        {
                            'type': 'member_remove',
                            'memberName': f'{member["firstname"]} {member["lastname"]}',
                            'memberId': member_id,
                            'userId': user_id,
                            'userName': session.get('name', 'Anonymous User'),
                            'timestamp': datetime.now().isoformat()
                        }
                    )
            else:
                flash('Member removed successfully.', 'success')
        else:
            flash('Failed to remove member from project.', 'error')
            
    except Exception as e:
        print(f"Remove member error: {e}")
        flash('An error occurred while removing the member.', 'error')
    
    return redirect(url_for('view_members', project_id=project_id))

def project_add_member(project_id):
    try:
        user_id = session.get('user_id')

        if not project_id or not ObjectId.is_valid(project_id):
            print(f"Invalid project ID format: {project_id}")
            flash('Invalid project ID.', 'error')
            return redirect(url_for('projects'))
        
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

                socketio = get_socketio()
                if socketio:
                    broadcast_to_project(
                        project_id,
                        'member_added',
                        {
                            'type': 'member_add',
                            'memberName': f'{member["firstname"]} {member["lastname"]}',
                            'memberId': str(member_object_id),
                            'userId': user_id,
                            'userName': session.get('name', 'Anonymous User'),
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                
                return redirect(url_for('view_members', project_id=project_id))
            else:
                flash('Failed to add member to project.', 'error')
                return render_template('/main/add_member.html', project=project)
        
        return render_template('/main/add_member.html', project=project)
        
    except Exception as e:
        print(f"Add member error: {e}")
        flash('An error occurred while adding the member.', 'error')
        return redirect(url_for('projects'))
    
def project_delete_confirm(project_id):
    try:
        user_id = session.get('user_id')
        
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            'user_id': user_id
        })
        
        if not project:
            flash('Project not found or you do not have permission to delete it.', 'error')
            return redirect(url_for('projects'))
        
        tasks_count = tasks_collection.count_documents({'project_id': ObjectId(project_id)})
        columns_count = column_collection.count_documents({'project': ObjectId(project_id)})
        members_count = len(project.get('members', []))
        
        return render_template('/main/delete_project.html',
                             project=project,
                             tasks_count=tasks_count,
                             columns_count=columns_count,
                             members_count=members_count)
        
    except Exception as e:
        print(f"Project delete confirm error: {e}")
        flash('An error occurred.', 'error')
        return redirect(url_for('projects'))
    
def project_delete(project_id):
    try:
        user_id = session.get('user_id')
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            'user_id': user_id
        })
        
        if not project:
            flash('Project not found or you do not have permission to delete it. Only the project owner can delete projects.', 'error')
            return redirect(url_for('projects'))
        
        project_name = project.get('project_name', 'Unknown Project')
        tasks_result = tasks_collection.delete_many({'project_id': ObjectId(project_id)})
        columns_result = column_collection.delete_many({'project': ObjectId(project_id)})
        project_result = projects_collection.delete_one({'_id': ObjectId(project_id)})
        
        if project_result.deleted_count > 0:
            socketio = get_socketio()
            if socketio:
                broadcast_to_project(
                    project_id,
                    'project_deleted',
                    {
                        'type': 'project_delete',
                        'projectId': project_id,
                        'projectName': project_name,
                        'userId': user_id,
                        'userName': session.get('name', 'Anonymous User'),
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            flash(f'Project "{project_name}" and all associated data deleted successfully! ({tasks_result.deleted_count} tasks, {columns_result.deleted_count} columns)', 'success')
        else:
            flash('Failed to delete project.', 'error')
        
        return redirect(url_for('projects'))
        
    except Exception as e:
        print(f"Project delete error: {e}")
        flash('An error occurred while deleting the project.', 'error')
        return redirect(url_for('projects'))