<?php
//Returns "1" if load balancer has marked this instance for eviction. Else returns "0"
include "vghead.php";

//get and parse arguments
$localip = $_SERVER['REMOTE_ADDR'];

$conn = getDBConnection(); 

$query = "select * from farmstatus where localip = '$localip' and evict_order_time is not null";
$result = mysql_query($query, $conn);
if($row = mysql_fetch_array($result)){ //row present.
	echo 1;
}else{
	echo 0;
}

closeDBConnection($conn);

?>
