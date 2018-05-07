// Generated by the protocol buffer compiler.  DO NOT EDIT!
// source: slam_msg.proto

#ifndef PROTOBUF_slam_5fmsg_2eproto__INCLUDED
#define PROTOBUF_slam_5fmsg_2eproto__INCLUDED

#include <string>

#include <google/protobuf/stubs/common.h>

#if GOOGLE_PROTOBUF_VERSION < 3005000
#error This file was generated by a newer version of protoc which is
#error incompatible with your Protocol Buffer headers.  Please update
#error your headers.
#endif
#if 3005001 < GOOGLE_PROTOBUF_MIN_PROTOC_VERSION
#error This file was generated by an older version of protoc which is
#error incompatible with your Protocol Buffer headers.  Please
#error regenerate this file with a newer version of protoc.
#endif

#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/arena.h>
#include <google/protobuf/arenastring.h>
#include <google/protobuf/generated_message_table_driven.h>
#include <google/protobuf/generated_message_util.h>
#include <google/protobuf/metadata.h>
#include <google/protobuf/message.h>
#include <google/protobuf/repeated_field.h>  // IWYU pragma: export
#include <google/protobuf/extension_set.h>  // IWYU pragma: export
#include <google/protobuf/unknown_field_set.h>
// @@protoc_insertion_point(includes)

namespace protobuf_slam_5fmsg_2eproto {
// Internal implementation detail -- do not use these members.
struct TableStruct {
  static const ::google::protobuf::internal::ParseTableField entries[];
  static const ::google::protobuf::internal::AuxillaryParseTableField aux[];
  static const ::google::protobuf::internal::ParseTable schema[1];
  static const ::google::protobuf::internal::FieldMetadata field_metadata[];
  static const ::google::protobuf::internal::SerializationTable serialization_table[];
  static const ::google::protobuf::uint32 offsets[];
};
void AddDescriptors();
void InitDefaultsSlamMsgImpl();
void InitDefaultsSlamMsg();
inline void InitDefaults() {
  InitDefaultsSlamMsg();
}
}  // namespace protobuf_slam_5fmsg_2eproto
namespace slam {
class SlamMsg;
class SlamMsgDefaultTypeInternal;
extern SlamMsgDefaultTypeInternal _SlamMsg_default_instance_;
}  // namespace slam
namespace slam {

// ===================================================================

class SlamMsg : public ::google::protobuf::Message /* @@protoc_insertion_point(class_definition:slam.SlamMsg) */ {
 public:
  SlamMsg();
  virtual ~SlamMsg();

  SlamMsg(const SlamMsg& from);

  inline SlamMsg& operator=(const SlamMsg& from) {
    CopyFrom(from);
    return *this;
  }
  #if LANG_CXX11
  SlamMsg(SlamMsg&& from) noexcept
    : SlamMsg() {
    *this = ::std::move(from);
  }

  inline SlamMsg& operator=(SlamMsg&& from) noexcept {
    if (GetArenaNoVirtual() == from.GetArenaNoVirtual()) {
      if (this != &from) InternalSwap(&from);
    } else {
      CopyFrom(from);
    }
    return *this;
  }
  #endif
  inline const ::google::protobuf::UnknownFieldSet& unknown_fields() const {
    return _internal_metadata_.unknown_fields();
  }
  inline ::google::protobuf::UnknownFieldSet* mutable_unknown_fields() {
    return _internal_metadata_.mutable_unknown_fields();
  }

  static const ::google::protobuf::Descriptor* descriptor();
  static const SlamMsg& default_instance();

  static void InitAsDefaultInstance();  // FOR INTERNAL USE ONLY
  static inline const SlamMsg* internal_default_instance() {
    return reinterpret_cast<const SlamMsg*>(
               &_SlamMsg_default_instance_);
  }
  static PROTOBUF_CONSTEXPR int const kIndexInFileMessages =
    0;

  void Swap(SlamMsg* other);
  friend void swap(SlamMsg& a, SlamMsg& b) {
    a.Swap(&b);
  }

  // implements Message ----------------------------------------------

  inline SlamMsg* New() const PROTOBUF_FINAL { return New(NULL); }

  SlamMsg* New(::google::protobuf::Arena* arena) const PROTOBUF_FINAL;
  void CopyFrom(const ::google::protobuf::Message& from) PROTOBUF_FINAL;
  void MergeFrom(const ::google::protobuf::Message& from) PROTOBUF_FINAL;
  void CopyFrom(const SlamMsg& from);
  void MergeFrom(const SlamMsg& from);
  void Clear() PROTOBUF_FINAL;
  bool IsInitialized() const PROTOBUF_FINAL;

  size_t ByteSizeLong() const PROTOBUF_FINAL;
  bool MergePartialFromCodedStream(
      ::google::protobuf::io::CodedInputStream* input) PROTOBUF_FINAL;
  void SerializeWithCachedSizes(
      ::google::protobuf::io::CodedOutputStream* output) const PROTOBUF_FINAL;
  ::google::protobuf::uint8* InternalSerializeWithCachedSizesToArray(
      bool deterministic, ::google::protobuf::uint8* target) const PROTOBUF_FINAL;
  int GetCachedSize() const PROTOBUF_FINAL { return _cached_size_; }
  private:
  void SharedCtor();
  void SharedDtor();
  void SetCachedSize(int size) const PROTOBUF_FINAL;
  void InternalSwap(SlamMsg* other);
  private:
  inline ::google::protobuf::Arena* GetArenaNoVirtual() const {
    return NULL;
  }
  inline void* MaybeArenaPtr() const {
    return NULL;
  }
  public:

  ::google::protobuf::Metadata GetMetadata() const PROTOBUF_FINAL;

  // nested types ----------------------------------------------------

  // accessors -------------------------------------------------------

  // required string id = 1;
  bool has_id() const;
  void clear_id();
  static const int kIdFieldNumber = 1;
  const ::std::string& id() const;
  void set_id(const ::std::string& value);
  #if LANG_CXX11
  void set_id(::std::string&& value);
  #endif
  void set_id(const char* value);
  void set_id(const char* value, size_t size);
  ::std::string* mutable_id();
  ::std::string* release_id();
  void set_allocated_id(::std::string* id);

  // optional double m_x = 2;
  bool has_m_x() const;
  void clear_m_x();
  static const int kMXFieldNumber = 2;
  double m_x() const;
  void set_m_x(double value);

  // optional double m_y = 3;
  bool has_m_y() const;
  void clear_m_y();
  static const int kMYFieldNumber = 3;
  double m_y() const;
  void set_m_y(double value);

  // optional double m_z = 4;
  bool has_m_z() const;
  void clear_m_z();
  static const int kMZFieldNumber = 4;
  double m_z() const;
  void set_m_z(double value);

  // optional double u_x = 5;
  bool has_u_x() const;
  void clear_u_x();
  static const int kUXFieldNumber = 5;
  double u_x() const;
  void set_u_x(double value);

  // optional double u_y = 6;
  bool has_u_y() const;
  void clear_u_y();
  static const int kUYFieldNumber = 6;
  double u_y() const;
  void set_u_y(double value);

  // optional double u_z = 7;
  bool has_u_z() const;
  void clear_u_z();
  static const int kUZFieldNumber = 7;
  double u_z() const;
  void set_u_z(double value);

  // @@protoc_insertion_point(class_scope:slam.SlamMsg)
 private:
  void set_has_id();
  void clear_has_id();
  void set_has_m_x();
  void clear_has_m_x();
  void set_has_m_y();
  void clear_has_m_y();
  void set_has_m_z();
  void clear_has_m_z();
  void set_has_u_x();
  void clear_has_u_x();
  void set_has_u_y();
  void clear_has_u_y();
  void set_has_u_z();
  void clear_has_u_z();

  ::google::protobuf::internal::InternalMetadataWithArena _internal_metadata_;
  ::google::protobuf::internal::HasBits<1> _has_bits_;
  mutable int _cached_size_;
  ::google::protobuf::internal::ArenaStringPtr id_;
  double m_x_;
  double m_y_;
  double m_z_;
  double u_x_;
  double u_y_;
  double u_z_;
  friend struct ::protobuf_slam_5fmsg_2eproto::TableStruct;
  friend void ::protobuf_slam_5fmsg_2eproto::InitDefaultsSlamMsgImpl();
};
// ===================================================================


// ===================================================================

#ifdef __GNUC__
  #pragma GCC diagnostic push
  #pragma GCC diagnostic ignored "-Wstrict-aliasing"
#endif  // __GNUC__
// SlamMsg

// required string id = 1;
inline bool SlamMsg::has_id() const {
  return (_has_bits_[0] & 0x00000001u) != 0;
}
inline void SlamMsg::set_has_id() {
  _has_bits_[0] |= 0x00000001u;
}
inline void SlamMsg::clear_has_id() {
  _has_bits_[0] &= ~0x00000001u;
}
inline void SlamMsg::clear_id() {
  id_.ClearToEmptyNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited());
  clear_has_id();
}
inline const ::std::string& SlamMsg::id() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.id)
  return id_.GetNoArena();
}
inline void SlamMsg::set_id(const ::std::string& value) {
  set_has_id();
  id_.SetNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited(), value);
  // @@protoc_insertion_point(field_set:slam.SlamMsg.id)
}
#if LANG_CXX11
inline void SlamMsg::set_id(::std::string&& value) {
  set_has_id();
  id_.SetNoArena(
    &::google::protobuf::internal::GetEmptyStringAlreadyInited(), ::std::move(value));
  // @@protoc_insertion_point(field_set_rvalue:slam.SlamMsg.id)
}
#endif
inline void SlamMsg::set_id(const char* value) {
  GOOGLE_DCHECK(value != NULL);
  set_has_id();
  id_.SetNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited(), ::std::string(value));
  // @@protoc_insertion_point(field_set_char:slam.SlamMsg.id)
}
inline void SlamMsg::set_id(const char* value, size_t size) {
  set_has_id();
  id_.SetNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited(),
      ::std::string(reinterpret_cast<const char*>(value), size));
  // @@protoc_insertion_point(field_set_pointer:slam.SlamMsg.id)
}
inline ::std::string* SlamMsg::mutable_id() {
  set_has_id();
  // @@protoc_insertion_point(field_mutable:slam.SlamMsg.id)
  return id_.MutableNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited());
}
inline ::std::string* SlamMsg::release_id() {
  // @@protoc_insertion_point(field_release:slam.SlamMsg.id)
  clear_has_id();
  return id_.ReleaseNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited());
}
inline void SlamMsg::set_allocated_id(::std::string* id) {
  if (id != NULL) {
    set_has_id();
  } else {
    clear_has_id();
  }
  id_.SetAllocatedNoArena(&::google::protobuf::internal::GetEmptyStringAlreadyInited(), id);
  // @@protoc_insertion_point(field_set_allocated:slam.SlamMsg.id)
}

// optional double m_x = 2;
inline bool SlamMsg::has_m_x() const {
  return (_has_bits_[0] & 0x00000002u) != 0;
}
inline void SlamMsg::set_has_m_x() {
  _has_bits_[0] |= 0x00000002u;
}
inline void SlamMsg::clear_has_m_x() {
  _has_bits_[0] &= ~0x00000002u;
}
inline void SlamMsg::clear_m_x() {
  m_x_ = 0;
  clear_has_m_x();
}
inline double SlamMsg::m_x() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.m_x)
  return m_x_;
}
inline void SlamMsg::set_m_x(double value) {
  set_has_m_x();
  m_x_ = value;
  // @@protoc_insertion_point(field_set:slam.SlamMsg.m_x)
}

// optional double m_y = 3;
inline bool SlamMsg::has_m_y() const {
  return (_has_bits_[0] & 0x00000004u) != 0;
}
inline void SlamMsg::set_has_m_y() {
  _has_bits_[0] |= 0x00000004u;
}
inline void SlamMsg::clear_has_m_y() {
  _has_bits_[0] &= ~0x00000004u;
}
inline void SlamMsg::clear_m_y() {
  m_y_ = 0;
  clear_has_m_y();
}
inline double SlamMsg::m_y() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.m_y)
  return m_y_;
}
inline void SlamMsg::set_m_y(double value) {
  set_has_m_y();
  m_y_ = value;
  // @@protoc_insertion_point(field_set:slam.SlamMsg.m_y)
}

// optional double m_z = 4;
inline bool SlamMsg::has_m_z() const {
  return (_has_bits_[0] & 0x00000008u) != 0;
}
inline void SlamMsg::set_has_m_z() {
  _has_bits_[0] |= 0x00000008u;
}
inline void SlamMsg::clear_has_m_z() {
  _has_bits_[0] &= ~0x00000008u;
}
inline void SlamMsg::clear_m_z() {
  m_z_ = 0;
  clear_has_m_z();
}
inline double SlamMsg::m_z() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.m_z)
  return m_z_;
}
inline void SlamMsg::set_m_z(double value) {
  set_has_m_z();
  m_z_ = value;
  // @@protoc_insertion_point(field_set:slam.SlamMsg.m_z)
}

// optional double u_x = 5;
inline bool SlamMsg::has_u_x() const {
  return (_has_bits_[0] & 0x00000010u) != 0;
}
inline void SlamMsg::set_has_u_x() {
  _has_bits_[0] |= 0x00000010u;
}
inline void SlamMsg::clear_has_u_x() {
  _has_bits_[0] &= ~0x00000010u;
}
inline void SlamMsg::clear_u_x() {
  u_x_ = 0;
  clear_has_u_x();
}
inline double SlamMsg::u_x() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.u_x)
  return u_x_;
}
inline void SlamMsg::set_u_x(double value) {
  set_has_u_x();
  u_x_ = value;
  // @@protoc_insertion_point(field_set:slam.SlamMsg.u_x)
}

// optional double u_y = 6;
inline bool SlamMsg::has_u_y() const {
  return (_has_bits_[0] & 0x00000020u) != 0;
}
inline void SlamMsg::set_has_u_y() {
  _has_bits_[0] |= 0x00000020u;
}
inline void SlamMsg::clear_has_u_y() {
  _has_bits_[0] &= ~0x00000020u;
}
inline void SlamMsg::clear_u_y() {
  u_y_ = 0;
  clear_has_u_y();
}
inline double SlamMsg::u_y() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.u_y)
  return u_y_;
}
inline void SlamMsg::set_u_y(double value) {
  set_has_u_y();
  u_y_ = value;
  // @@protoc_insertion_point(field_set:slam.SlamMsg.u_y)
}

// optional double u_z = 7;
inline bool SlamMsg::has_u_z() const {
  return (_has_bits_[0] & 0x00000040u) != 0;
}
inline void SlamMsg::set_has_u_z() {
  _has_bits_[0] |= 0x00000040u;
}
inline void SlamMsg::clear_has_u_z() {
  _has_bits_[0] &= ~0x00000040u;
}
inline void SlamMsg::clear_u_z() {
  u_z_ = 0;
  clear_has_u_z();
}
inline double SlamMsg::u_z() const {
  // @@protoc_insertion_point(field_get:slam.SlamMsg.u_z)
  return u_z_;
}
inline void SlamMsg::set_u_z(double value) {
  set_has_u_z();
  u_z_ = value;
  // @@protoc_insertion_point(field_set:slam.SlamMsg.u_z)
}

#ifdef __GNUC__
  #pragma GCC diagnostic pop
#endif  // __GNUC__

// @@protoc_insertion_point(namespace_scope)

}  // namespace slam

// @@protoc_insertion_point(global_scope)

#endif  // PROTOBUF_slam_5fmsg_2eproto__INCLUDED
