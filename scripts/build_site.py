#!/usr/bin/env python3
"""
Build script for the Lesson Portal
Processes YAML lesson files and generates static site
"""

import os
import json
import yaml
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Configuration
CONFIG = {
    'github_org': 'your-org',  # Replace with your GitHub org
    'github_repo': 'public-lessons',  # Replace with your public repo name
    'instructor_repo': 'instructor-materials',  # Replace with instructor repo name
    'instructor_email': 'instructor-access@university.edu',  # Replace with your email
    'base_url': 'https://your-org.github.io/lesson-portal'  # Replace with your site URL
}

def load_yaml_file(filepath):
    """Load and parse a YAML file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_lesson_id_from_filename(filename):
    """Extract lesson ID from YAML filename"""
    return Path(filename).stem

def process_lesson_data(lesson_data, lesson_id):
    """Process lesson data and add computed fields"""
    lesson_data['id'] = lesson_id
    
    # Handle legacy formats - convert to materials if needed
    if 'notebook' in lesson_data and 'materials' not in lesson_data:
        # Convert single notebook to materials format
        lesson_data['materials'] = [{
            'title': lesson_data['title'],
            'description': lesson_data['description'],
            'type': 'notebook',
            'url': f"https://github.com/{CONFIG['github_org']}/{CONFIG['github_repo']}/blob/main/{lesson_data.get('public_repo_path', lesson_id)}/{lesson_data['notebook']['filename']}",
            'duration': lesson_data['notebook']['duration']
        }]
    elif 'notebooks' in lesson_data and 'materials' not in lesson_data:
        # Convert notebooks array to materials format
        lesson_data['materials'] = []
        for nb in lesson_data['notebooks']:
            lesson_data['materials'].append({
                'title': nb['title'],
                'description': nb['description'],
                'type': 'notebook',
                'url': f"https://github.com/{CONFIG['github_org']}/{CONFIG['github_repo']}/blob/main/{lesson_data.get('public_repo_path', lesson_id)}/{nb['filename']}",
                'duration': nb['duration']
            })
    
    return lesson_data

def build_lessons_json(lessons_dir, output_dir):
    """Build the lessons.json file from all YAML files"""
    lessons = []
    
    # Process all YAML files in lessons directory
    for yaml_file in Path(lessons_dir).glob('*.yml'):
        print(f"Processing {yaml_file.name}...")
        
        lesson_data = load_yaml_file(yaml_file)
        lesson_id = get_lesson_id_from_filename(yaml_file.name)
        lesson_data = process_lesson_data(lesson_data, lesson_id)
        
        lessons.append(lesson_data)
    
    # Sort lessons by title
    lessons.sort(key=lambda x: x['title'])
    
    # Write lessons.json
    output_file = Path(output_dir) / 'lessons.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {output_file} with {len(lessons)} lessons")
    return lessons

def build_lesson_pages(lessons, templates_dir, output_dir):
    """Build individual lesson pages from template"""
    
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Load lesson template
    template = env.get_template('lesson.html')
    
    for lesson in lessons:
        print(f"Building lesson page for {lesson['id']}...")
        
        # Create lesson directory
        lesson_dir = Path(output_dir) / 'lessons' / lesson['id']
        lesson_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare template context
        context = {
            **lesson,  # All lesson data
            **CONFIG   # Configuration data
        }
        
        # Render template
        html_content = template.render(context)
        
        # Write lesson page
        lesson_file = lesson_dir / 'index.html'
        with open(lesson_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Generated {lesson_file}")

def copy_static_files(source_dir, output_dir):
    """Copy index.html and any static assets"""
    
    # Copy index.html directly
    index_source = Path(source_dir) / 'index.html'
    index_dest = Path(output_dir) / 'index.html'

    css_source = Path(source_dir) / 'theme.css'
    css_dest = Path(output_dir) / 'theme.css'

    logo_source = Path(source_dir) / 'act-cms-logo.svg'
    logo_dest = Path(output_dir) / 'act-cms-logo.svg'
    
    if index_source.exists():
        shutil.copy2(index_source, index_dest)
        print(f"Copied {index_source} to {index_dest}")
    else:
        print(f"Warning: {index_source} not found")

    if css_source.exists():
        shutil.copy2(css_source, css_dest)
        print(f"Copied {css_source} to {css_dest}") 
    else:
        print(f"Warning: {css_source} not found")

    if logo_source.exists():
        shutil.copy2(logo_source, logo_dest)
        print(f"Copied {logo_source} to {logo_dest}")
    else:
        print(f"Warning: {logo_source} not found")   
    
    # Copy static directory if it exists
    static_source = Path(source_dir) / 'static'
    static_dest = Path(output_dir) / 'static'
    
    if static_source.exists():
        if static_dest.exists():
            shutil.rmtree(static_dest)
        shutil.copytree(static_source, static_dest)
        print(f"Copied static files from {static_source} to {static_dest}")

def validate_lesson_data(lesson_data, filename):
    """Validate lesson data has required fields"""
    required_fields = [
        'title', 'description', 'programming_skill', 'primary_course',
        'authors', 'format', 'scientific_objectives', 
        'cyberinfrastructure_objectives', 'platforms'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in lesson_data:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"Warning: {filename} is missing required fields: {missing_fields}")
        return False
    
    # Check for materials OR legacy notebook formats
    has_materials = 'materials' in lesson_data
    has_notebooks = 'notebooks' in lesson_data
    has_notebook = 'notebook' in lesson_data
    
    if not (has_materials or has_notebooks or has_notebook):
        print(f"Warning: {filename} has no materials, notebooks, or notebook field")
        return False
    
    # Validate materials structure if present
    if has_materials:
        if not isinstance(lesson_data['materials'], list):
            print(f"Warning: {filename} materials field must be a list")
            return False
        
        for i, material in enumerate(lesson_data['materials']):
            required_material_fields = ['title', 'description', 'type', 'url', 'duration']
            for field in required_material_fields:
                if field not in material:
                    print(f"Warning: {filename} material {i+1} is missing required field: {field}")
                    return False
    
    # Validate authors field
    if 'authors' in lesson_data:
        authors = lesson_data['authors']
        if not isinstance(authors, (list, str)):
            print(f"Warning: {filename} authors field must be a list or string")
            return False
    
    return True

def main():
    """Main build process"""
    print("Building Lesson Portal...")
    
    # Define paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    lessons_dir = project_root / 'lessons'
    templates_dir = project_root / 'templates'
    output_dir = project_root / 'site'  # This will be pushed to gh-pages
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Validate required directories exist
    if not lessons_dir.exists():
        print(f"Error: Lessons directory {lessons_dir} not found")
        return 1
    
    if not templates_dir.exists():
        print(f"Error: Templates directory {templates_dir} not found")
        return 1
    
    # Check for YAML files
    yaml_files = list(lessons_dir.glob('*.yml'))
    if not yaml_files:
        print(f"Error: No .yml files found in {lessons_dir}")
        return 1
    
    print(f"Found {len(yaml_files)} lesson files")
    
    # Validate all lesson files first
    valid_lessons = True
    for yaml_file in yaml_files:
        lesson_data = load_yaml_file(yaml_file)
        if not validate_lesson_data(lesson_data, yaml_file.name):
            valid_lessons = False
    
    if not valid_lessons:
        print("Error: Some lesson files have validation errors")
        return 1
    
    try:
        # Build lessons.json
        lessons = build_lessons_json(lessons_dir, output_dir)
        
        # Build individual lesson pages
        build_lesson_pages(lessons, templates_dir, output_dir)
        
        # Copy static files
        copy_static_files(project_root, output_dir)
        
        print(f"\n✅ Build complete! Site generated in {output_dir}")
        print(f"📄 Generated {len(lessons)} lesson pages")
        print(f"🔗 Lessons available at: /lessons/[lesson-id]/")
        
        return 0
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())