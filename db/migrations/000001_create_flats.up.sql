

CREATE TABLE flats (
   url text not null,
   found_ts text,
   title text,
   picture_url text,
   summary_location text,
   price INTEGER,
   updated_at text,
   filter_name text not null,
   PRIMARY KEY (url, filter_name)
)


