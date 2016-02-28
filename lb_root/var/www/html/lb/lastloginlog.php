<?php

function login2db($username, $ip){
	$conn = getDBConnection_users();
	$query = "update users set last_login = NOW(), last_login_ip='$ip' where username='$username'";
	mysql_query($query);
	$query = "update users set first_login=last_login where username='$username' and first_login is NULL";
	mysql_query($query);
	$query = "update registry set ivalue = ivalue + 1 where var='user sessions'";
	mysql_query($query);
	closeDBConnection_users($conn);
}


function getDBConnection_users(){
	$conn = mysql_pconnect("localhost", "ashwin", "ashVG@119");
	mysql_select_db("users", $conn);
	return $conn;
}

function closeDBConnection_users($conn){
	mysql_close($conn);
}

?>
