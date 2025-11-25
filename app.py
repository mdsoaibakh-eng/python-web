import os
from flask import Flask, render_template, redirect, url_for, flash, request
from dotenv import load_dotenv
from models import db, Item
from markupsafe import Markup, escape

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '123456')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')  # e.g. mysql+pymysql://user:pass@host:port/db
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ''
        return Markup('<br>'.join(escape(s).splitlines()))

    @app.route('/')
    def index():
        page = request.args.get('page', 1, type=int)
        per_page = 6
        items = Item.query.order_by(Item.created_at.desc()).paginate(page=page, per_page=per_page)
        return render_template('list.html', items=items)

    @app.route('/item/<int:item_id>')
    def detail(item_id):
        item = Item.query.get_or_404(item_id)
        return render_template('detail.html', item=item)

    @app.route('/create', methods=['GET', 'POST'])
    def create():
        if request.method == 'POST':
            title = (request.form.get('title') or '').strip()
            description = (request.form.get('description') or '').strip() or None

            errors = []
            if not title:
                errors.append('Title is required.')
            if errors:
                for e in errors:
                    flash(e, 'error')
                
                return render_template('create.html', title=title, description=description)
            item = Item(title=title, description=description)
            db.session.add(item)
            db.session.commit()
            flash('Item created successfully.', 'success')
            return redirect(url_for('index'))

        return render_template('create.html', title='', description='')

    @app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
    def edit(item_id):
        item = Item.query.get_or_404(item_id)
        if request.method == 'POST':
            title = (request.form.get('title') or '').strip()
            description = (request.form.get('description') or '').strip() or None

            errors = []
            if not title:
                errors.append('Title is required.')
            if errors:
                for e in errors:
                    flash(e, 'error')
                return render_template('edit.html', item=item, title=title, description=description)

            item.title = title
            item.description = description
            db.session.commit()
            flash('Item updated.', 'success')
            return redirect(url_for('detail', item_id=item.id))

        return render_template('edit.html', item=item, title=item.title, description=item.description or '')

    @app.route('/delete/<int:item_id>', methods=['POST'])
    def delete(item_id):
        item = Item.query.get_or_404(item_id)
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted.', 'info')
        return redirect(url_for('index'))

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    return app

if __name__ == '__main__':
    create_app().run(debug=True)
