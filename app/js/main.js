var config;
var rank = {
    TOO_SHORT: 0,
    WEAK: 1,
    MEDIUM: 2,
    STRONG: 3,
    VERY_STRONG: 4
};
$(function() {
  $.getJSON("config.json")
  .done(function(data){
    console.log(data);
    config = data;
  });
  addListeners();

  $('input[name="password1"]').tooltipster({
    trigger: 'custom',
    position: 'right',
    contentAsHTML: true
  });

  $('input[name="password2"]').tooltipster({
    trigger: 'custom',
    position: 'right',
    content: "Passwords don't match"
  });
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
  $('input[name="password1"]').keyup( function () {
    var password = $('input[name="password1"]').val();
    if(password.length>0){
      $(this).tooltipster('show');
      testPassword(password);
    }
    else{
      $(this).tooltipster('hide');
    }
  })
  .focus( function() {
    var password = $(this).val();
    if(password.length>0){
      $(this).tooltipster('show');
    }
  })
  .blur( function() {
    $(this).tooltipster('hide');
  });

  $('input[name="password2"]').keyup( function () {
    var password1 = $('input[name="password1"]').val();
    var password2 = $('input[name="password2"]').val();
    if(password1 !== password2){
      $(this).tooltipster('show');
    }
    else{
      $(this).tooltipster('hide');
    }
  })
  .focus( function() {
    var password1 = $('input[name="password1"]').val();
    var password2 = $('input[name="password2"]').val();
    if(password1 !== password2){
      $(this).tooltipster('show');
    }
  })
  .blur( function() {
    $(this).tooltipster('hide');
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
      document.location.assign(currentURL.origin+currentURL.pathname+"../"+currentURL.hash);
    }
    else{
      document.location.assign(currentURL.origin+currentURL.pathname+"../");
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
  else if (testPassword(password1)<2){
    $(".login-message").html("Password need to be at least 'Medium' strength try adding some numbers or symbols.");
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
      //TODO: implement a fail counter that asks them to send an email to support if it fails more than 2 times
      $(".login-message").html("Token is invalid, please request a new password again.");
      $("#login-form").removeClass('denied').width(); // reading width() forces reflow
      $("#login-form").addClass('denied');
    }
    if(data.status === 404){
      $(".login-message").html("Could not find login server.");
    }
  });
}

function testPassword(password){
  var result = rankPassword(password),
      labels = ["Too Short", "Weak", "Medium", "Strong", "Very Strong"],
      tooltipContent = "<b>"+labels[result]+"</b><br>";

  if (result === 0) {
    tooltipContent += "<span class='tooltip-password-hint'>Your password needs to be over 8 characters.</span>";
  }
  else if (result === 1) {
    tooltipContent += "<span class='tooltip-password-hint'>Your password is too weak, try adding some numbers or capitalising a letter.</span>";
  }
  else if (result === 2) {
    tooltipContent += "<span class='tooltip-password-hint'>Your password is OK, adding some symbols(#!@&) should make it better.</span>";
  }
  else if (result === 3) {
    tooltipContent += "<span class='tooltip-password-hint'>Your password is good.</span>";
  }
  else if (result === 4) {
    tooltipContent += "<span class='tooltip-password-hint'>Your password is very good.</span>";
  }
  if($('input[name="password1"]').tooltipster('content') !== tooltipContent){
    $('input[name="password1"]').tooltipster('content', tooltipContent);
  }
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

//Taken from https://www.safaribooksonline.com/library/view/regular-expressions-cookbook/9781449327453/ch04s19.html
function rankPassword(password) {
    var upper = /[A-Z]/,
        lower = /[a-z]/,
        number = /[0-9]/,
        special = /[^A-Za-z0-9]/,
        minLength = 8,
        score = 0;

    if (password.length < minLength) {
        return rank.TOO_SHORT; // End early
    }

    // Increment the score for each of these conditions
    if (upper.test(password)) score++;
    if (lower.test(password)) score++;
    if (number.test(password)) score++;
    if (special.test(password)) score++;

    // Penalize if there aren't at least three char types
    if (score < 3) score--;

    if (password.length > minLength) {
        // Increment the score for every 2 chars longer than the minimum
        score += Math.floor((password.length - minLength) / 2);
    }

    // Return a ranking based on the calculated score
    if (score < 3) return rank.WEAK; // score is 2 or lower
    if (score < 4) return rank.MEDIUM; // score is 3
    if (score < 6) return rank.STRONG; // score is 4 or 5
    return rank.VERY_STRONG; // score is 6 or higher
}
