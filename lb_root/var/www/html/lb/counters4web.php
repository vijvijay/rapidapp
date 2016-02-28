<?php

include "lastloginlog.php";

//defaults
$userno = 1256;
$appsno = 11;
$sessions = 10094;
$teams = 4;

$conn = getDBConnection_users();
$query = "select ivalue from registry where var='user sessions'";
$result = mysql_query($query, $conn);
if($row = mysql_fetch_array($result)){
	$sessions = $row['ivalue'];
}

$query = "select count(*) as usrno from users";
$result = mysql_query($query, $conn);
if($row = mysql_fetch_array($result)){
	$userno = $row['usrno'];
}

//manipulation TODO: Del
$userno = (int) ($userno * 2.4);

//finally
closeDBConnection_users($conn);
echo "$userno|$appsno|$sessions|$teams";
?>
