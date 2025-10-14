from db import projects_collection, column_collection, tasks_collection, users_collection
from utils.socket import broadcast_to_project, get_socketio
from flask import request, flash, redirect, url_for, session, jsonify, render_template
from bson import ObjectId
from datetime import datetime, timedelta

def my_tasks():
    user_id = session.get('user_id')
    
    # Find all tasks assigned to the current user
    tasks_cursor = tasks_collection.find({'assigned_to': user_id})
    tasks_list = list(tasks_cursor)

    enriched_tasks = []
    for task in tasks_list:
        # Get project details
        project = projects_collection.find_one({'_id': task['project_id']})
        
        # Get column details
        column = column_collection.find_one({'_id': task['column_id']})

        # Enrich task with additional information
        task['project_name'] = project.get('project_name', 'Unknown Project') if project else 'Unknown Project'
        task['project_color'] = project.get('color', '#3b82f6') if project else '#3b82f6'
        task['column_name'] = column.get('label', 'Unknown Column') if column else 'Unknown Column'
        
        enriched_tasks.append(task)
    
    now = datetime.now()
    
    overdue_tasks = []
    due_soon_tasks = []
    other_tasks = []
    
    # Categorize tasks based on due date
    for task in enriched_tasks:
        due_date = task.get('due_date')
        
        if due_date:
            # Make sure due_date is a datetime object
            if isinstance(due_date, datetime):
                if due_date < now:
                    overdue_tasks.append(task)
                elif due_date <= now + timedelta(days=7):
                    due_soon_tasks.append(task)
                else:
                    other_tasks.append(task)
        else:
            other_tasks.append(task)
    
    # Sort tasks by due date
    overdue_tasks.sort(key=lambda x: x.get('due_date', datetime.min))
    due_soon_tasks.sort(key=lambda x: x.get('due_date', datetime.min))
    
    return render_template('tasks/tasks.html', 
                         tasks=enriched_tasks,
                         overdue_tasks=overdue_tasks,
                         due_soon_tasks=due_soon_tasks,
                         other_tasks=other_tasks)

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

def task_update(project_id, task_id):
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

        task = tasks_collection.find_one({
            '_id': ObjectId(task_id),
            'project_id': ObjectId(project_id)
        })
        
        if not task:
            flash('Task not found.', 'error')
            return redirect(url_for('view_project', project_id=project_id))
        
        if request.method == 'POST':
            title = request.form['title'].strip()
            description = request.form.get('description', '').strip()
            task_type = request.form.get('type', 'task').strip()
            priority = request.form.get('priority', 'medium').strip()
            due_date_str = request.form.get('due_date', '').strip()
            column_id = request.form['column_id'].strip()
            labels_str = request.form.get('labels', '').strip()
            assigned_to = request.form.get('assigned_to', user_id).strip()

            if not title:
                flash('Task title is required!', 'error')
                return redirect(url_for('update_task', project_id=project_id, task_id=task_id))
            
            column = column_collection.find_one({
                '_id': ObjectId(column_id),
                'project': ObjectId(project_id)
            })
            
            if not column:
                flash('Invalid column selected.', 'error')
                return redirect(url_for('update_task', project_id=project_id, task_id=task_id))

            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid due date format.', 'error')
                    return redirect(url_for('update_task', project_id=project_id, task_id=task_id))

            labels = []
            if labels_str:
                labels = [label.strip() for label in labels_str.split(',') if label.strip()]

            assignee_info = users_collection.find_one({'_id': ObjectId(assigned_to)})
            if assignee_info:
                assignee_name = f"{assignee_info.get('firstname', '')} {assignee_info.get('lastname', '')}".strip()
                assignee_initials = ''.join([name[0].upper() for name in assignee_name.split() if name])[:2]
            else:
                assignee_name = 'Unassigned'
                assignee_initials = 'U'

            update_data = {
                'title': title,
                'description': description,
                'type': task_type,
                'priority': priority,
                'due_date': due_date,
                'labels': labels,
                'column_id': ObjectId(column_id),
                'assigned_to': assigned_to,
                'assignee_name': assignee_name,
                'assignee_initials': assignee_initials,
                'updated_at': datetime.now()
            }

            if str(task['column_id']) != column_id:
                last_task = tasks_collection.find_one(
                    {'column_id': ObjectId(column_id)},
                    sort=[('order', -1)]
                )
                next_order = (last_task.get('order', -1) + 1) if last_task else 0
                update_data['order'] = next_order
            
            result = tasks_collection.update_one(
                {'_id': ObjectId(task_id)},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                socketio = get_socketio()
                if socketio:
                    broadcast_to_project(
                        project_id,
                        'task_updated',
                        {
                            'type': 'task_update',
                            'taskId': task_id,
                            'task': {
                                '_id': task_id,
                                'title': title,
                                'description': description,
                                'type': task_type,
                                'priority': priority,
                                'due_date': due_date.isoformat() if due_date else None,
                                'labels': labels,
                                'assignee_name': assignee_name,
                                'assignee_initials': assignee_initials
                            },
                            'userId': user_id,
                            'userName': session.get('name', 'Anonymous User'),
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                
                return redirect(url_for('view_project', project_id=project_id))
            else:
                flash('No changes were made to the task.', 'info')
                return redirect(url_for('view_project', project_id=project_id))

        columns = list(column_collection.find({'project': ObjectId(project_id)}).sort('order', 1))
        project_members = list(users_collection.find({'_id': {'$in': project.get('members', [])}}))
        
        return render_template('/main/update_task.html', 
                             project=project, 
                             task=task,
                             columns=columns,
                             members=project_members)
        
    except Exception as e:
        print(f"Task update error: {e}")
        flash('An error occurred while updating the task.', 'error')
        return redirect(url_for('view_project', project_id=project_id))

def task_delete(project_id, task_id):
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

        task = tasks_collection.find_one({
            '_id': ObjectId(task_id),
            'project_id': ObjectId(project_id)
        })
        
        if not task:
            flash('Task not found.', 'error')
            return redirect(url_for('view_project', project_id=project_id))
    
        task_title = task.get('title', 'Unknown Task')
        column_id = str(task.get('column_id'))

        result = tasks_collection.delete_one({'_id': ObjectId(task_id)})
        
        if result.deleted_count > 0:
            socketio = get_socketio()
            if socketio:
                broadcast_to_project(
                    project_id,
                    'task_deleted',
                    {
                        'type': 'task_delete',
                        'taskId': task_id,
                        'taskTitle': task_title,
                        'columnId': column_id,
                        'userId': user_id,
                        'userName': session.get('name', 'Anonymous User'),
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
        else:
            flash('Failed to delete task.', 'error')
        
        return redirect(url_for('view_project', project_id=project_id))
        
    except Exception as e:
        print(f"Task delete error: {e}")
        flash('An error occurred while deleting the task.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
def task_view_detail(project_id, task_id):
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
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        task = tasks_collection.find_one({
            '_id': ObjectId(task_id),
            'project_id': ObjectId(project_id)
        })
        
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'}), 404

        column = column_collection.find_one({
            '_id': task['column_id']
        })

        task_data = {
            '_id': str(task['_id']),
            'title': task.get('title', ''),
            'description': task.get('description', ''),
            'type': task.get('type', 'task'),
            'priority': task.get('priority', 'medium'),
            'due_date': task['due_date'].strftime('%b %d, %Y') if task.get('due_date') else None,
            'created_at': task['created_at'].strftime('%b %d, %Y') if task.get('created_at') else None,
            'labels': task.get('labels', []),
            'assignee_name': task.get('assignee_name', 'Unassigned'),
            'assignee_initials': task.get('assignee_initials', 'U'),
            'column_name': column.get('label', '') if column else '',
            'column_color': column.get('color', 'light-blue') if column else 'light-blue',
            'project_name': project.get('project_name', ''),
            'project_id': str(project['_id'])
        }

        return jsonify({
            'success': True,
            'task': task_data
        })
        
    except Exception as e:
        print(f"Task detail view error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500