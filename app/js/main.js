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

  $( "#forgot-form" ).submit(function( event ) {
    event.preventDefault();
    forgotPassword();
  });

  $( "#reset-form" ).submit(function( event ) {
    event.preventDefault();
    resetPassword();
  });
}

function login(){
  var username = $("input[name='username']").val();
  var password = $("input[name='password']").val();
  var passwordHashed = sha1(password);
  var currentURL = document.location;
  console.log(currentURL);

  $(".login-message").html("Logging in");
  $.post("/api/login",
    {
      username:username,
      password:passwordHashed
    })
  .done(function(data, status){
    //move the browser location to the new url
    var hash;
    if(currentURL.hash!==""){
      console.log(currentURL.hash);
      document.location.assign(currentURL.origin+currentURL.pathname+"/../"+currentURL.hash);
    }
    else{
      document.location.assign(currentURL.origin+currentURL.pathname+"/../");
      //document.location.assign(currentURL.origin+config.successURL);
    }
    //document.location.assign(currentURL.origin+config.successURL);
  })
  .fail(function(data){
    if(data.status === 403){
      $(".login-message").html("Username or password invalid.");
      $("#login-form").removeClass('denied').width(); // reading width() forces reflow
      $("#login-form").addClass('denied');
    }
    if(data.status === 404){
      $(".login-message").html("Could not find login server.");
    }
  });
}

function resetPassword(){
  var formError = false;
  var password1 = $("input[name='password1']").val();
  var password2 = $("input[name='password2']").val();


  if(password1 !== password2){
    $(".login-message").html("Passwords don't match.");
    formError = true;
  }
  else if (password1 === "" && password2 === "") {
    $(".login-message").html("Passwords not set.");
    formError = true;
  }
  else{
    formError = false;
  }

  if(formError){
    $("#login-form").removeClass('denied').width(); // reading width() forces reflow
    $("#login-form").addClass('denied');
    return;
  }

  var newPasswordHash = sha1(password1);
  var token = getQueryVariable("token");
  console.log(token);
  if (token === undefined || token === false) {
    //hopefully this doesn't happen.
    $(".login-message").html("Could not find token, try following the link in your email again.");
    return;
  }

  $.post("/api/resetpassword",
    {
      newPasswordHash:newPasswordHash,
      token:token
    })
  .done(function(data, status){
    //move the browser location to the new url
    $(".login-message").html("Password Reset.");
  })
  .fail(function(data){
    if(data.status === 403){
      $(".login-message").html("Username or password invalid.");
      $("#login-form").removeClass('denied').width(); // reading width() forces reflow
      $("#login-form").addClass('denied');
    }
    if(data.status === 404){
      $(".login-message").html("Could not find login server.");
    }
  });
}

function forgotPassword(){
  var formError = false;
  var username = $("input[name='username']").val();
  var email = $("input[name='email']").val();

  //$("#forgot-form").fadeOut();

   if (email===""&&username==="") {
    $(".login-message").html("We need your username & email to reset your password.");
    $("input[name='email']").addClass("inputError");
    $("input[name='username']").addClass("inputError");
    formError = true;
  }
  else if(username===""){
    $(".login-message").html("We need your username to reset your password.");
    $("input[name='username']").addClass("inputError");
    formError = true;
  }
  else if (email==="") {
    $(".login-message").html("We need your email to reset your password.");
    $("input[name='email']").addClass("inputError");
    formError = true;
  }
  else {
    formError = false;
  }

  if(formError){
    $("#login-form").removeClass('denied').width(); // reading width() forces reflow
    $("#login-form").addClass('denied');
    return;
  }

  $.post("/api/resetrequest",
    {
      username:username,
      email:email
    })
  .done(function(data, status){
    //move the browser location to the new url
    $(".login-message").html("Email sent to "+email);
  })
  .fail(function(data){
    if(data.status === 400){
      $(".login-message").html("Something went wrong, please contact <a href='mailto:support@lemonadelabs.io'>support</a>.");
    }
    if(data.status === 404){
      $(".login-message").html("Could not find login server.");
    }
  });
}

//taken from https://css-tricks.com/snippets/javascript/get-url-variables/
function getQueryVariable(variable)
{
       var query = window.location.search.substring(1);
       var vars = query.split("&");
       for (var i=0;i<vars.length;i++) {
               var pair = vars[i].split("=");
               if(pair[0] == variable){return pair[1];}
       }
       return(false);
}
