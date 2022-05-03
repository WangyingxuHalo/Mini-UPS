from django.urls import path, include

import my_ups.views

urlpatterns = [
    path('home', my_ups.views.home_page),
    path('home_cn', my_ups.views.home_page_cn),
    path('services', my_ups.views.services_page),
    path('services_cn', my_ups.views.services_page_cn),
    path('teams', my_ups.views.team_page),
    path('teams_cn', my_ups.views.team_page_cn),
    path('login', my_ups.views.login_page),
    path('login_cn', my_ups.views.login_page_cn),
    path('feedback', my_ups.views.feedback_page),
    path('feedback_cn', my_ups.views.feedback_page_cn),
    path('user_login', my_ups.views.user_login),
    path('user_login_cn', my_ups.views.user_login_cn),
    path('register', my_ups.views.user_register),
    path('profile', my_ups.views.profile_page),
    path('profile_cn', my_ups.views.profile_page_cn),
    path('profile_history', my_ups.views.profile_history),
    path('profile_history_cn', my_ups.views.profile_history_cn),
    path('packages_search', my_ups.views.packages_search),
    path('package_change_address', my_ups.views.package_change_address),
    path('logout', my_ups.views.logout),
    path('logout_cn', my_ups.views.logout_cn),
    path('search_certain_packages/<int:package_id>', my_ups.views.search_certain_packages),
    path('get_messages', my_ups.views.get_messages),
    path('get_user_messages', my_ups.views.get_user_messages),
    path('send_message', my_ups.views.send_message),
    path('package_change_password', my_ups.views.package_change_password),
    path('forget_password', my_ups.views.forget_password),
    path('forget_password_cn', my_ups.views.forget_password_cn),
    path('reset_password/<str:username>', my_ups.views.reset_password),
    path('reset_password_cn/<str:username>', my_ups.views.reset_password_cn),
    path('reset_change_password', my_ups.views.reset_change_password),
    path('reset_change_password_cn', my_ups.views.reset_change_password_cn),
    path('provide_feedback', my_ups.views.provide_feedback)
]