# -*- coding: utf-8 -*-
###############################################################################
#
#    OpenEduCat Inc
#    Copyright (C) 2009-TODAY OpenEduCat Inc(<http://www.openeducat.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class OpStudentCourse(models.Model):
    _name = "op.student.course"
    _description = "Student Course Details"
    _inherit = "mail.thread"
    _rec_name = 'student_id'

    student_id = fields.Many2one('op.student', 'Student',
                                 ondelete="cascade", index=True)
    course_id = fields.Many2one('op.course', 'Course', required=True, index=True)
    batch_id = fields.Many2one('op.batch', 'Batch', required=True, index=True)
    roll_number = fields.Char('Roll Number')
    subject_ids = fields.Many2many('op.subject', string='Subjects', index=True)
    academic_years_id = fields.Many2one('op.academic.year', 'Academic Year')
    academic_term_id = fields.Many2one('op.academic.term', 'Terms')
    state = fields.Selection([('running', 'Running'),
                              ('finished', 'Finished')],
                             string="Status", default="running")

    _sql_constraints = [
        ('unique_name_roll_number_id',
         'unique(roll_number,course_id,batch_id,student_id)',
         'Roll Number & Student must be unique per Batch!'),
        ('unique_name_roll_number_course_id',
         'unique(roll_number,course_id,batch_id)',
         'Roll Number must be unique per Batch!'),
        ('unique_name_roll_number_student_id',
         'unique(student_id,course_id,batch_id)',
         'Student must be unique per Batch!'),
    ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Student Course Details'),
            'template': '/openeducat_core/static/xls/op_student_course.xls'
        }]


class OpStudent(models.Model):
    _name = "op.student"
    _description = "Student"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {"res.partner": "partner_id"}

    first_name = fields.Char('First Name',  translate=True)
    middle_name = fields.Char('Middle Name', translate=True)
    last_name = fields.Char('Last Name', translate=True)
    birth_date = fields.Date('Birth Date')
    blood_group = fields.Selection([
        ('A+', 'A+ve'),
        ('B+', 'B+ve'),
        ('O+', 'O+ve'),
        ('AB+', 'AB+ve'),
        ('A-', 'A-ve'),
        ('B-', 'B-ve'),
        ('O-', 'O-ve'),
        ('AB-', 'AB-ve')
    ], string='Blood Group')
    gender = fields.Selection([
        ('m', 'Male'),
        ('f', 'Female'),
        ('o', 'Other')
    ], 'Gender', required=True, default='m')
    nationality = fields.Many2one('res.country', 'Nationality')
    emergency_contact = fields.Many2one('res.partner', 'Emergency Contact')
    visa_info = fields.Char('Visa Info', size=64)
    id_number = fields.Char('ID Card Number', size=64)
    partner_id = fields.Many2one('res.partner', 'Partner',
                                 required=True, ondelete="cascade")
    user_id = fields.Many2one('res.users', 'User', ondelete="cascade")
    gr_no = fields.Char("GR Number", size=20, index=True)
    category_id = fields.Many2one('op.category', 'Category')
    course_detail_ids = fields.One2many('op.student.course', 'student_id',
                                        'Course Details',
                                         index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [(
        'unique_gr_no',
        'unique(gr_no)',
        'GR Number must be unique per student!'
    )]

    @api.onchange('first_name', 'middle_name', 'last_name')
    def _onchange_name(self):
        if not self.middle_name:
            self.name = str(self.first_name) + " " + str(
                self.last_name
            )
        else:
            self.name = str(self.first_name) + " " + str(
                self.middle_name) + " " + str(self.last_name)

    @api.constrains('birth_date')
    def _check_birthdate(self):
        for record in self:
            if record.birth_date > fields.Date.today():
                raise ValidationError(_(
                    "Birth Date can't be greater than current date!"))

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/openeducat_core/static/xls/op_student.xls'
        }]
        
    def create_student_user(self):
        user_group = self.env.ref("base.group_portal") or False
        users_res = self.env['res.users']
        for record in self:
            if not record.user_id:
                user_id = users_res.create({
                    'name': record.name,
                    'partner_id': record.partner_id.id,
                    'login': record.email,
                    'groups_id': user_group,
                    'is_student': True,
                    'tz': self._context.get('tz'),
                    'oauth_uid': record.email if record.email else False,
                    'oauth_provider_id': self.env['auth.oauth.provider'].search([('name', '=', 'Azure AD Single Tenant')], limit=1).id if self.env['auth.oauth.provider'].search([('name', '=', 'Azure AD Single Tenant')], limit=1) else False,

                })
                record.user_id = user_id
                
    @api.model      
    def create_student_user_batch(self):
        # Use sudo() to bypass access rights checking if it's safe to do so
        self = self.sudo()
        
        user_group = self.env.ref("base.group_portal", raise_if_not_found=False)
        users_res = self.env['res.users']

        # Filter records that don't have a user_id assigned
        records_without_user = self.filtered(lambda record: not record.user_id)

        # Prepare user data in bulk
        user_values_list = []
        for record in records_without_user:
            user_values_list.append({
                'name': record.name,
                'partner_id': record.partner_id.id,
                'login': record.email if record.email else record.gr_no,
                'groups_id': [(6, 0, [user_group.id])] if user_group else [],
                'is_student': True,
                'tz': self._context.get('tz'),
                'oauth_uid': record.email if record.email else False,
                'oauth_provider_id': self.env['auth.oauth.provider'].search([('name', '=', 'Azure AD Single Tenant')], limit=1).id if self.env['auth.oauth.provider'].search([('name', '=', 'Azure AD Single Tenant')], limit=1) else False,
            })

                
        if user_values_list:
            failed = False
            try:
                # Attempt to create users in bulk
                new_users = users_res.create(user_values_list)
            except Exception as e:
                # Log the bulk creation error
                _logger.error(f"Bulk creation failed for users")
                _logger.error(f"Error details: {e}")
                failed = True
                
            if failed:
                # Initialize an empty list to store successfully created users
                new_users = []
                
                # Retry creating users one by one
                for user_values in user_values_list:
                    try:
                        new_user = users_res.create(user_values)
                        new_users.append(new_user)
                        self.env.cr.commit() 
                    except Exception as individual_error:
                        # Log the error for the individual user
                        _logger.error(f"Failed to create user: {user_values}")
                        _logger.error(f"Error details: {individual_error}")
                        # Continue with the next user, effectively dropping the problematic user
                        self.env.cr.rollback()

            # Assign the newly created user_ids back to the respective records
            for record, user_id in zip(records_without_user, new_users):
                record.user_id = user_id


