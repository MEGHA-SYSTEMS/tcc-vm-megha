from flask import Blueprint, render_template, request, flash, redirect, url_for

medical_bp = Blueprint('medical', __name__)

@medical_bp.route('/medical', methods=['GET', 'POST'])
def medical():
    return render_template('medical/medical.html')