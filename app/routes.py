from flask import Blueprint, render_template, request, jsonify

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@main_bp.route('/api/hello', methods=['GET'])
def hello_api():
    """API endpoint example"""
    name = request.args.get('name', 'World')
    return jsonify({'message': f'Hello, {name}!'})

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')
