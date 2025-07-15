require 'sinatra'
require 'json'
require 'sqlite3'
require_relative 'my_user_model'

set('views', './views')
set :port, 8080
set :bind, '0.0.0.0'
enable :sessions

get '/users' do
    user = User.all.map { |user| user.to_h.reject {|k, _| k == :password}}
    content_type :json
    { users: user }.to_json
end

post '/users' do
    content_type :json
    user_info = {
        firstname: params[:firstname],
        lastname: params[:lastname],
        age: params[:age].to_i,
        password: params[:password],
        email: params[:email]
    }
    user = User.create(user_info)
    user1 = User.all.map {|user| user.to_h.reject { |k, _| k == :password }}
    
    body user1.to_json
end

post '/sign_in' do
    content_type :json
  
    user_id = User.findCredential(params[:email], params[:password])
    if user_id.nil?
      halt 401, { error: "Email ou mot de passe incorrect" }.to_json
    end
  
    user = User.find(user_id)
    if user && user.password == params[:password]
      session[:user_id] = user.id
      user.to_h.reject { |k, _| k == :password }.to_json
    else
      halt 401, { error: "Email ou mot de passe incorrect" }.to_json
    end
  end
  

put '/users' do
    content_type :json
    halt 401, body({ error: "Non autorise" }.to_json) unless session[:user_id]
    User.update(session[:user_id], "password", params[:password])
    user = User.find(session[:user_id])
    body user.to_h.reject { |k, _| k == :password }.to_json
end

delete '/users' do
    content_type :json
    halt 401, body({ error: "Non autorise" }.to_json) unless session[:user_id]
    User.destroy(session[:user_id])
    session.clear
    user = User.all.map { |user| user.to_h.reject {|k, _| k == :password}}
    
    status 204
    body ''
end

get '/' do
    @users = User.all.map { |user| user.to_h.reject {|k, _| k == :password}}
    erb :index
end