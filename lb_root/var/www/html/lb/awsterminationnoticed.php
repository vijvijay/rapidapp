<?php
//Mark the termination_noticed column to true for this localip
include "vghead.php";

//get and parse arguments
$localip = $_SERVER['REMOTE_ADDR'];

$conn = getDBConnection(); 

//update farmstatus and say this node is no more available for new sessions
$query = "update farmstatus set termination_noticed=true, donot_allocate=-1 where localip = '$localip'";
mysql_query($query, $conn);

//remove existing user session mappings to this node from sessions table
$query = "delete from sessions where localip = '$localip'";
mysql_query($query, $conn);

closeDBConnection($conn);

?>
