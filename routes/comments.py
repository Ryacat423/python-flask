from flask import request, session, jsonify
from bson import ObjectId
from datetime import datetime
from db import comments_collection, tasks_collection, projects_collection

def comment_create(project_id, task_id):
    try:
        data = request.get_json()
        comment_text = data.get('comment')
        user_id = session.get('user_id')
        user_name = session.get('name', 'Anonymous')
        
        if not comment_text or not comment_text.strip():
            return jsonify({'success': False, 'message': 'Comment text is required'}), 400
        
        task = tasks_collection.find_one({
            '_id': ObjectId(task_id),
            'project_id': ObjectId(project_id)
        })
        
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'}), 404
        
        project = projects_collection.find_one({
            '_id': ObjectId(project_id),
            '$or': [
                {'user_id': user_id},
                {'members': ObjectId(user_id)}
            ]
        })
        
        if not project:
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        comment = {
            'task_id': ObjectId(task_id),
            'project_id': ObjectId(project_id),
            'user_id': user_id,
            'user_name': user_name,
            'comment': comment_text.strip(),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'edited': False
        }
        
        result = comments_collection.insert_one(comment)
        comment['_id'] = result.inserted_id

        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'comment': {
                '_id': str(comment['_id']),
                'user_name': comment['user_name'],
                'user_id': comment['user_id'],
                'comment': comment['comment'],
                'created_at': comment['created_at'].isoformat(),
                'edited': comment['edited']
            }
        })
        
    except Exception as e:
        print(f"Comment create error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


def comment_list(project_id, task_id):
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
        
        comments = list(comments_collection.find(
            {'task_id': ObjectId(task_id)},
            sort=[('created_at', -1)]
        ))

        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                '_id': str(comment['_id']),
                'user_name': comment['user_name'],
                'user_id': comment['user_id'],
                'comment': comment['comment'],
                'created_at': comment['created_at'].isoformat(),
                'edited': comment.get('edited', False),
                'can_edit': comment['user_id'] == user_id
            })
        
        return jsonify({
            'success': True,
            'comments': formatted_comments
        })
        
    except Exception as e:
        print(f"Comment list error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


def comment_update(project_id, task_id, comment_id):
    try:
        data = request.get_json()
        comment_text = data.get('comment')
        user_id = session.get('user_id')
        
        if not comment_text or not comment_text.strip():
            return jsonify({'success': False, 'message': 'Comment text is required'}), 400

        comment = comments_collection.find_one({
            '_id': ObjectId(comment_id),
            'task_id': ObjectId(task_id),
            'user_id': user_id
        })
        
        if not comment:
            return jsonify({'success': False, 'message': 'Comment not found or access denied'}), 404

        result = comments_collection.update_one(
            {'_id': ObjectId(comment_id)},
            {
                '$set': {
                    'comment': comment_text.strip(),
                    'updated_at': datetime.now(),
                    'edited': True
                }
            }
        )
        
        if result.modified_count > 0:
            return jsonify({
                'success': True,
                'message': 'Comment updated successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to update comment'}), 500
            
    except Exception as e:
        print(f"Comment update error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


def comment_delete(project_id, task_id, comment_id):
    try:
        user_id = session.get('user_id')
        
        comment = comments_collection.find_one({
            '_id': ObjectId(comment_id),
            'task_id': ObjectId(task_id),
            'user_id': user_id
        })
        
        if not comment:
            return jsonify({'success': False, 'message': 'Comment not found or access denied'}), 404

        result = comments_collection.delete_one({'_id': ObjectId(comment_id)})
        
        if result.deleted_count > 0:
            return jsonify({
                'success': True,
                'message': 'Comment deleted successfully'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to delete comment'}), 500
            
    except Exception as e:
        print(f"Comment delete error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500