import datetime
import os
import sys
    

project = u'metatools'
copyright = u'%s, Western X' % datetime.datetime.utcnow().year

version = '0.1'
release = '0.1'

extensions = [
    'sphinx.ext.autodoc', 
    'sphinx.ext.extlinks',
    'sphinx.ext.graphviz',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

html_logo = '_static/westernx_small_logo.png'
master_doc = 'index'
pygments_style = 'sphinx'

exclude_patterns = ['_build']
html_static_path = ['_static']
templates_path = ['_templates']

autodoc_member_order = 'bysource'
autodoc_default_flags = ['undoc-members']

todo_include_todos = True

intersphinx_mapping = {
    'python': ('http://docs.python.org/release/2.6.8/', None),
}
