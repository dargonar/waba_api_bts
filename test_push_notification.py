from  notificator import *

account_name  = 'pablo'
message				= 'nada'
data					= { 
			'pn_type' 		: 'tipo', 
			'pn_title' 		: 'titulo', 
			'pn_content' 	: 'content', 
			'pn_link' 		: 'link', 
			'pn_img_url' 	: 'img_url',
			'pn_comercio' : 'comercio',
			'pn_airdrop' 	: '100'
		}

push_notification(account_name, message, data)
