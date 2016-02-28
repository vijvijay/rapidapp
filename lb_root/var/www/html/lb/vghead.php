<?php

function getDBConnection(){
	$conn = mysql_pconnect("localhost", "loadbalancer", "apprimelb");
	mysql_select_db("ec2farm", $conn);
	return $conn;
}

function closeDBConnection($conn){
	mysql_close($conn);
}

?>
