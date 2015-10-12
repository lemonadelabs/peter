var config;

$(function() {
  $.getJSON("config.json")
  .done(function(data){
    console.log(data);
    config = data;
  });
  addListeners();
});

function addListeners() {
  $( "#login-form" ).submit(function( event ) {
    event.preventDefault();
    login();
  });
  $("#login").click(function(){
    login();
  });
}

function login(){
  var username = $("input[name='username']").val();
  var password = $("input[name='password']").val();
  var passwordHashed = md5(password);
  var currentURL = document.location;
  $(".login-message").html("Logging in");
  $.post("/api/login",
    {
      username:username,
      password:passwordHashed
    })
  .done(function(data, status){
    //move the browser location to the new url
    console.log(currentURL);
    /*if(currentURL.hash!==undefined){
      document.location.assign(currentURL.origin+config.successURL);
    }*/
  })
  .fail(function(data){
    if(data.status === 403){
      $(".login-message").html("Username or password invalid.");
      $(".login-box").addClass("denied");
    }
    if(data.status === 404){
      $(".login-message").html("Could not find login server.");
    }
  });
}
