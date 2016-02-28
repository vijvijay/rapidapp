<?php
error_reporting(E_ALL);

function vg_getNextUidNumber(){
	$conn = getDBConnection();
	mysql_query("lock tables nextuid write");
	$result = mysql_query("select * from nextuid");
	$row = mysql_fetch_array($result);
	$uidNum = $row['nextuid'];
	mysql_query("update nextuid set nextuid = nextuid + 1");
	mysql_query("unlock tables");
	closeDBConnection($conn);
	return $uidNum;
}

//Private functions follow
function getDBConnection(){
	$conn = mysql_pconnect("localhost", "ashwin", "ashVG@119");
	mysql_select_db("users", $conn);
	return $conn;
}

function closeDBConnection($conn){
	mysql_close($conn);
}

?>
