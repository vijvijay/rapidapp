<?php

include "vghead.php";

//get and parse arguments
$uid 		= $_REQUEST['uid'];
$state	 	= $_REQUEST['state'];
$localip	= $_SERVER['REMOTE_ADDR'];

$conn = getDBConnection(); 
if($state == 'session_started'){
	$query = "select * from farmstatus where localip = '$localip'";
	$result = mysql_query($query, $conn);
	if($row = mysql_fetch_array($result)){ //node with this localip is in our farm.
		$instanceid	= $row['instanceid'];
		$publicip	= $row['publicip'];

		$query = "select * from sessions where userid = '$uid'";
		$result1 = mysql_query($query, $conn);
		if($row1 = mysql_fetch_array($result1)){
			//already a row for this user's session is present. Should be in suspended mode.
			$query = "update sessions set session_state='live' where userid = '$uid' and localip='$localip'";
			mysql_query($query, $conn);
		}else{
			//row not present, as it should be
			//insert new row
			$query = "insert into sessions (userid, session_state, instanceid, localip, publicip, creation_time) values
					('$uid', 'live', '$instanceid', '$localip', '$publicip', NOW())";
			mysql_query($query, $conn);
		}
	}
}else if($state == 'session_suspended'){
	$query = "update sessions set session_state='suspended' where userid = '$uid' and localip='$localip'";
	mysql_query($query, $conn);
}else if($state == 'session_terminated'){
	$query = "delete from sessions where userid = '$uid' and localip='$localip'";
	mysql_query($query, $conn);
}

closeDBConnection($conn);

?>
