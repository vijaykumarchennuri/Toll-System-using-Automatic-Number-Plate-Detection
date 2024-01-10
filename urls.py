from django.urls import path

from . import views

urlpatterns = [path("index.html", views.index, name="index"),
			path("Signup.html", views.Signup, name="Signup"),
			path("SignupAction", views.SignupAction, name="SignupAction"),	    	
			path("UserLogin.html", views.UserLogin, name="UserLogin"),
			path("UserLoginAction", views.UserLoginAction, name="UserLoginAction"),
			path("AdminLogin.html", views.AdminLogin, name="AdminLogin"),
			path("AdminLoginAction", views.AdminLoginAction, name="AdminLoginAction"),
			path("RechargeAccount.html", views.RechargeAccount, name="RechargeAccount"),
			path("RechargeAccountAction", views.RechargeAccountAction, name="RechargeAccountAction"),
			path("CollectPayment.html", views.CollectPayment, name="CollectPayment"),
			path("CollectPaymentAction", views.CollectPaymentAction, name="CollectPaymentAction"),
			path("ViewPayment", views.ViewPayment, name="ViewPayment"),
			path("ViewBalance", views.ViewBalance, name="ViewBalance"),
]