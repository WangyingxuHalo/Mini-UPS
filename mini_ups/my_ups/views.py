from django.shortcuts import render
from django.contrib import auth
from django.shortcuts import render, redirect
from .models import Package, Messages, Feedback
from .models import MyUser as User
from django.http import JsonResponse
from django.forms.models import model_to_dict
import json
from django.core.mail import EmailMessage
import datetime
from django.db.models import Q

# Create your views here.
def home_page(request):
    return render(request, 'my_ups/homepage.html')

def home_page_cn(request):
    return render(request, 'my_ups/homepage-cn.html')

def services_page(request):
    return render(request, 'my_ups/services.html')

def services_page_cn(request):
    return render(request, 'my_ups/services-cn.html')

def team_page(request):
    return render(request, 'my_ups/teammember.html')

def team_page_cn(request):
    return render(request, 'my_ups/teammember-cn.html')

def feedback_page(request):
    return render(request, 'my_ups/feedback.html')

def feedback_page_cn(request):
    return render(request, 'my_ups/feedback-cn.html')

def login_page(request):
    if request.user.is_authenticated:
        return render(request, 'my_ups/index.html')
    else:
        return render(request, 'my_ups/login.html')

def login_page_cn(request):
    if request.user.is_authenticated:
        return render(request, 'my_ups/index-cn.html')
    else:
        return render(request, 'my_ups/login-cn.html')

def profile_page(request):
    if request.user.is_authenticated:
        return render(request, 'my_ups/index.html')
    else:
        return redirect('/ups/login')

def profile_page_cn(request):
    if request.user.is_authenticated:
        return render(request, 'my_ups/index-cn.html')
    else:
        return redirect('/ups/login_cn')

def profile_history(request):
    if request.user.is_authenticated:
        return render(request, 'my_ups/table-datatable-basic.html')
    else:
        return redirect('/ups/login')

def profile_history_cn(request):
    if request.user.is_authenticated:
        return render(request, 'my_ups/table-datatable-basic-cn.html')
    else:
        return redirect('/ups/login_cn')

def search_certain_packages(request, package_id):
    if request.user.is_authenticated:
        ret_json = {"content":[]}
        packages = Package.objects.filter(packageid=package_id)
        print(packages)
        for package in packages:
            ret_json["content"].append(model_to_dict(package))
        return JsonResponse(ret_json, status=200)
    else:
        return redirect('/ups/login')

def user_register(request):
    if request.method == "GET":
        print("get")
        return render(request, 'my_ups/login.html')
    elif request.method == "POST":
        print("post")
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get("email")
        if len(username) == 0 | len(password) == 0 | len(email) == 0:
            print("format not correct")
            return render(request, 'my_ups/login.html', {

                'regis_error': 'Each field cannot be empty'
            })
        count = User.objects.filter(username=username).count()
        if count == 0:
            print("register successfully, go to management page")
            user = User.objects.create_user(username, email, password)
            auth.login(request, user)
            if username != "yingxu":
                Messages.objects.create(message_from=1, message_from_name='yingxu', message_to=user.id, message_to_name=username, message='Hi, I am the administrator from Mini-UPS Group. If you need any help you can contact me.', time_sent=datetime.datetime.now())
                # Messages.objects.create(message_from=user.id, message_from_name=username, message_to=1, message_to_name='yingxu', message='Test Message', time_sent=datetime.datetime.now())
            return redirect('/ups/profile', {'user', user})
        else:
            print("account already exists")
            return render(request, 'my_ups/login.html', {
                'regis_error': 'already have the username'
            })

def user_login(request):
    if request.method == "GET":
        print("get")
        return render(request, 'my_ups/login.html')
    elif request.method == "POST":
        print("post")
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('/ups/profile', {'user', user})
        else:
            print("wrong")
            return render(request, 'my_ups/login.html', {
                'login_error' : 'username or password incorrect'
            })

def user_login_cn(request):
    if request.method == "GET":
        print("get")
        return render(request, 'my_ups/login_cn.html')
    elif request.method == "POST":
        print("post")
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('/ups/profile_cn', {'user', user})
        else:
            print("wrong")
            return render(request, 'my_ups/login_cn.html', {
                'login_error' : 'username or password incorrect'
            })

def packages_search(request):
    if request.user.is_authenticated:
        ret_json = {"content":[]}
        print(request.user.id)
        packages = Package.objects.filter(userid=request.user.id).order_by('-packageid')
        print(packages)
        for package in packages:
            ret_json["content"].append(model_to_dict(package))
        return JsonResponse(ret_json, status=200)
    else:
        return redirect('/ups/login')

def forget_password(request):
    req = json.loads(request.body.decode('utf-8'))
    email_addr = req['email_address']
    user_name = req['user_name']
    user = User.objects.get(username=user_name, email=email_addr)
    if user == None:
        return JsonResponse({"status":"failure","error_msg":f"Either email or user name is not correct"}, status=200)
    click_url = 'http://vcm-23688.vm.duke.edu:8000/ups/reset_password/' + user_name
    print(click_url) 
    subject_str = f' Password Reset for user %s' % user.username
    content_str = f'''Dear %s, 

Click here to reset your password:
%s

From:  
Mini-UPS ''' % (str(user.username), click_url)
    email = EmailMessage(subject_str, content_str, to=[email_addr])
    email.send()
    return JsonResponse({"status":"Success"}, status=200)

def forget_password_cn(request):
    req = json.loads(request.body.decode('utf-8'))
    email_addr = req['email_address']
    user_name = req['user_name']
    user = User.objects.get(username=user_name, email=email_addr)
    if user == None:
        return JsonResponse({"status":"failure","error_msg":f"Either email or user name is not correct"}, status=200)
    click_url = 'http://vcm-23688.vm.duke.edu:8000/ups/reset_password_cn/' + user_name
    print(click_url) 
    subject_str = f' 用户 %s 密码重置' % user.username
    content_str = f'''亲爱的 %s, 

点击这里来重置你的密码:
%s

来自:  
Mini-UPS ''' % (str(user.username), click_url)
    email = EmailMessage(subject_str, content_str, to=[email_addr])
    email.send()
    return JsonResponse({"status":"Success"}, status=200)

def reset_change_password(request):
    if request.method == "GET":
        return render(request, 'my_ups/login.html')
    elif request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        new_user = User.objects.get(username=username)
        email = new_user.email
        new_user.set_password(password)
        new_user.save()
        subject_str = f' Password Change successfully for user %s' % username
        content_str = f'''Dear %s, 

The password for user: %s has been changed successfully!

From:  
Mini-UPS ''' % (username, username)
        # send_email_to(email,subject_str,content_str)
        email = EmailMessage(subject_str, content_str, to=[email])
        email.send()
        return redirect('/ups/login')

def reset_change_password_cn(request):
    if request.method == "GET":
        return render(request, 'my_ups/login_cn.html')
    elif request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        new_user = User.objects.get(username=username)
        email = new_user.email
        new_user.set_password(password)
        new_user.save()
        subject_str = f' 用户 %s 修改密码成功' % username
        content_str = f'''亲爱的 %s, 

用户: %s 的密码修改成功!

来自:  
Mini-UPS ''' % (username, username)
        # send_email_to(email,subject_str,content_str)
        email = EmailMessage(subject_str, content_str, to=[email])
        email.send()
        return redirect('/ups/login_cn')

def package_change_password(request):
    if request.user.is_authenticated:
        req = json.loads(request.body.decode('utf-8'))
        username = request.user.username
        origin_password = req['original_pass']
        new_password = req['new_pass']
        user = auth.authenticate(username=username, password=origin_password)
        print(user)
        if user is not None:
            new_user = User.objects.get(username=username)
            new_user.set_password(new_password)
            new_user.save()
            subject_str = f' Password Change successfully for user %s' % request.user.username
            content_str = f'''Dear %s, 

The password for user: %s has been changed successfully!

From:  
Mini-UPS ''' % (str(request.user.username), str(request.user.username))
            email = EmailMessage(subject_str, content_str, to=[request.user.email])
            email.send()
            # send_email_to([request.user.email],subject_str,content_str)
            return JsonResponse({"status":"Success"}, status=200)
        else:
            return JsonResponse({"status":"failure","error_msg":f"Original password is not correct"}, status=200)
    else:
        return redirect('/ups/login')

def package_change_address(request):
    if request.user.is_authenticated:
        req = json.loads(request.body.decode('utf-8'))
        package = Package.objects.get(packageid=int(req['package_id']))
        curr_status = package.packagestatus
        if package.packagestatus == 1 or package.packagestatus == 2:
            package.destinationx = req['des_x']
            package.destinationy = req['des_y']
            package.save()
            subject_str = f' Destination Changed for Package #%s' % req['package_id']
            content_str = f'''Dear %s, 

The destination for package #%s has been changed to 
    
Destination X: %s  
Destination Y: %s 

From:  
Mini-UPS ''' % (str(request.user.username), req['package_id'], req['des_x'], req['des_y'])
            # send_email_to([request.user.email],subject_str,content_str)
            email = EmailMessage(subject_str, content_str, to=[request.user.email])
            email.send()
            return JsonResponse({"status":"Success"}, status=200)
        else:
            return JsonResponse({"status":"failure","error_msg":f"Status of this package is: %s"%(curr_status)}, status=200)
    else:
        return redirect('/ups/login')

def logout(request):
    if request.user.is_authenticated:
        auth.logout(request)
    return redirect('/ups/login')

def logout_cn(request):
    if request.user.is_authenticated:
        auth.logout(request)
    return redirect('/ups/login_cn')

def get_messages(request):
    if request.user.is_authenticated:
        ret_json = {"content":[]}
        # messages = Messages.objects.filter(to=request.user.id)
        names = Messages.objects.filter(message_to_name=request.user.username).values_list('message_from_name').distinct()
        for each_name in names:
            cur_name = each_name[0]
            ret_each = {cur_name:[]}
            person_message = Messages.objects.filter(message_to_name=request.user.username, message_from_name=cur_name) | Messages.objects.filter(message_to_name=cur_name, message_from_name=request.user.username)
            res = person_message.order_by('time_sent')
            for each_message in res:
                ret_each[cur_name].append(model_to_dict(each_message))
            ret_json["content"].append(ret_each)
        return JsonResponse(ret_json, status=200)

    return redirect('/ups/login')

def get_user_messages(request):
    if request.user.is_authenticated:
        req = json.loads(request.body.decode('utf-8'))
        from_user = req['from_user']
        ret_json = {"content":[]}
        messages = Messages.objects.filter(message_to_name=request.user.username, message_from_name=from_user) | Messages.objects.filter(message_to_name=from_user, message_from_name=request.user.username)
        res_messages = messages.order_by('time_sent')
        for res_message in res_messages:
            ret_json["content"].append(model_to_dict(res_message))
        return JsonResponse(ret_json, status=200)
    else:
        return redirect('/ups/login')

def send_message(request):
    if request.user.is_authenticated:
        req = json.loads(request.body.decode('utf-8'))
        input_message = req['input_message']
        send_to = req['send_to']
        Messages.objects.create(message_from=request.user.id, message_from_name=request.user.username, message_to_name=send_to, message=input_message, time_sent=datetime.datetime.now())
        print("create successfully")
        ret_json = {"content":[]}
        messages = Messages.objects.filter(message_to_name=request.user.username, message_from_name=send_to) | Messages.objects.filter(message_to_name=send_to, message_from_name=request.user.username)
        res_messages = messages.order_by('time_sent')
        for res_message in res_messages:
            ret_json["content"].append(model_to_dict(res_message))
        return JsonResponse(ret_json, status=200)
    else:
        return redirect('/ups/login')

def reset_password(request, username):
    return render(request, 'my_ups/reset.html', {
                'user_name' : username
            })

def reset_password_cn(request, username):
    return render(request, 'my_ups/reset-cn.html', {
                'user_name' : username
            })

def provide_feedback(request):
    if request.method == "GET":
        print("get")
        return render(request, 'my_ups/homepage.html')
    elif request.method == "POST":
        print("post")
        name = request.POST.get('name')
        email = request.POST.get('email')
        content = request.POST.get('content')
        Feedback.objects.create(name=name, email=email, content=content)
        return redirect('/ups/home')