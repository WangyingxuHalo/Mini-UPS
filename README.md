# ERSS-project-yw473-yh317

## This project is Mini-UPS. We develop it to cooperate with Mini-Amazon to deliver packages. <br>
Here in Mini-UPS, you can easily track your packages.<br>
<br>
Developer:<br>
Yiling Han yh317<br>
Yingxu Wang yw473<br>
<br>

### Protocol Difference
We provide protocol difference compared with previous version we submitted before.
Added protocols are colored blud and deleted protocols are colored red.

### Before Start
You need to have Django installed, as well as Postgres (including psycopg2) <br>
After that, you need to change the setting in directory: /mini_ups/mini_ups/settings.py about your databses settings <br>
Then, you can go to directory /mini_ups/ and run following codes:<br>
sudo python3 manage.py makemigrations my_ups<br>
<br>
After that, run: <br>
sudo python3 manage.py migrate <br>
Then the databases will be created for our services. Have fun with it! <br>

### We have Django part and server part. <br>
1. To run Django part, i.e., Mini-UPS Website, you can go to directory: /mini_ups and then run:<br>
sudo python3 manage.py runserver 0:8000<br>
<br>
After that, you can access website by url: <your url>:8000/ups/home<br>
For example, for us, the url is: http://vcm-23688.vm.duke.edu:8000/ups/home<br>
<br>


2. To run Server part, i.e., communication with Mini-Amazon, you can go to directory: mini_ups_backend and then run:<br>
python3 main.py<br>
<br>
To execute it successfully, you may need to have both world simulator and Mini-Amazon program. After that, you also need to change the url and port to those survices. <br>